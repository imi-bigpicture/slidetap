#    Copyright 2026 SECTRA AB
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.


"""Moving projects from one root schema to another, in steps."""

import logging
from typing import ClassVar
from uuid import UUID

from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from slidetap.database import (
    DatabaseMigrationObject,
    DatabaseProject,
    DatabaseProjectMigration,
)
from slidetap.model import (
    AnyAttribute,
    AttributeMigrationIssue,
    MigrationStatus,
    NotAllowedActionError,
    NotFoundError,
    Project,
    ProjectMigration,
    ProjectStatus,
)
from slidetap.services.attribute_service import AttributeService
from slidetap.services.database_service import DatabaseService
from slidetap.services.project_migration_executor import ProjectMigrationExecutor
from slidetap.services.project_migration_planner import (
    ObjectInMigration,
    ProjectMigrationPlanner,
    SearchItemInMigration,
)
from slidetap.services.review_service import ReviewService
from slidetap.services.schema_service import SchemaService
from slidetap.services.validation_service import ValidationService


class MigrationService:
    """Moves projects from the previous root schema they are on to the root of
    new projects, in steps.

    Created, the project is locked as migrating, and the migration planned in
    a task: run for every object without saving, with what it could not
    convert stored as attribute issues, as is every top-level attribute that
    was valid before and is not after, and every attribute with a value it
    dropped. The curator resolves each attribute issue, accepts each dropped
    attribute, and submits, which completes the migration in a task, or
    reverts.
    Completing runs the migration again, puts the resolved values at their
    tags, and replaces the attributes of every object, in one transaction for
    the whole project, which is validated again on the target root.

    Planning and completing run the migration with a `ProjectMigrationPlanner`,
    and completing writes it with a `ProjectMigrationExecutor`.
    """

    NO_MIGRATION_REFUSAL: ClassVar[str] = "its root has no migration"
    """Why a project whose root has no migration cannot be migrated."""

    NOT_MIGRATING_REFUSAL: ClassVar[str] = "it is not being migrated"
    """Why a started migration cannot go on with a project that is not
    migrating."""

    EXPORTED_REFUSAL: ClassVar[str] = "it has been exported"
    """Why an exported project cannot be migrated."""

    STORED_REFUSAL: ClassVar[str] = "its images are stored, or locked to be stored"
    """Why a project with stored images cannot be migrated."""

    BUSY_REFUSAL: ClassVar[str] = "batches are being searched or processed"
    """Why a project with busy batches cannot be migrated."""

    def __init__(
        self,
        schema_service: SchemaService,
        database_service: DatabaseService,
        attribute_service: AttributeService,
        validation_service: ValidationService,
        review_service: ReviewService,
    ):
        """Create the migration service.

        Parameters
        ----------
        schema_service: SchemaService
            For the roots, their migrations, and whether a project can be
            changed.
        database_service: DatabaseService
            For the sessions and the rows of the project.
        attribute_service: AttributeService
            For the display values of attributes.
        validation_service: ValidationService
            For validating the project on the target root.
        review_service: ReviewService
            For flagging review units left invalid.
        """
        self._schema_service = schema_service
        self._database_service = database_service
        self._attribute_service = attribute_service
        self._validation_service = validation_service
        self._review_service = review_service
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def create(self, project_uid: UUID) -> ProjectMigration:
        """Set the project as migrating, with a migration to be planned.

        A migration left from before, such as one that failed, is replaced.

        Parameters
        ----------
        project_uid: UUID
            The uid of the project.

        Returns
        -------
        ProjectMigration
            The migration, being planned.

        Raises
        ------
        NotFoundError
            If there is no such project.
        NotAllowedActionError
            If the project cannot be migrated, or not now.
        """
        with self._database_service.get_session() as session:
            project = self._lock_project(session, project_uid)
            self.assert_can_migrate(project, session)
            stale = self._database_service.get_optional_project_migration(
                session, project.uid
            )
            if stale is not None:
                session.delete(stale)
                session.flush()
            migration = DatabaseProjectMigration(
                project.uid,
                project.root_schema_uid,
                self._schema_service.default_root.uid,
                project.status,
            )
            session.add(migration)
            project.status = ProjectStatus.MIGRATING
            session.flush()
            self._logger.info(f"Project {project.uid} set as migrating.")
            return migration.model

    def plan(self, project_uid: UUID) -> None:
        """Run the migration of a project being planned without saving it, and
        store what it could not convert and what it dropped as attribute
        issues.

        Nothing is done where the project has no migration being planned.

        Parameters
        ----------
        project_uid: UUID
            The uid of the project.

        Raises
        ------
        NotFoundError
            If there is no such project.
        NotAllowedActionError
            If the project can no longer be migrated.
        MigrationError
            If the migration returns what it may not.
        """
        with self._database_service.get_session() as session:
            project = self._lock_project(session, project_uid)
            migration = self._database_service.get_optional_project_migration(
                session, project.uid
            )
            if migration is None or migration.status != MigrationStatus.PLANNING:
                self._logger.warning(
                    f"Project {project.uid} has no migration being planned."
                )
                return
            self.assert_can_migrate(project, session, started=True)
            planner = self._create_planner(project, migration)
            objects = self._migrate_objects(session, project, planner)
            # Checked now, as a search item the migration cannot move would
            # fail the completion.
            self._migrate_search_items(session, project, planner)
            for object_ in sorted(objects, key=lambda object_: object_.order):
                attribute_issues = list(planner.create_attribute_issues(object_))
                if attribute_issues:
                    migration.objects.append(
                        DatabaseMigrationObject(
                            object_.source.uid,
                            object_.target_schema.uid,
                            object_.identifier,
                            len(migration.objects),
                            attribute_issues,
                        )
                    )
            migration.set_status(MigrationStatus.CURATING)
            count = sum(len(object_.attribute_issues) for object_ in migration.objects)
            self._logger.info(
                f"Migration of project {project.uid} planned, with {count} "
                f"attribute issues."
            )

    def get(self, project_uid: UUID) -> ProjectMigration:
        """Get the migration of a project, with its plan.

        Parameters
        ----------
        project_uid: UUID
            The uid of the project.

        Returns
        -------
        ProjectMigration
            The migration, with its attribute issues by object.

        Raises
        ------
        NotFoundError
            If there is no such project, or it has no migration.
        """
        with self._database_service.get_session(commit=False) as session:
            project = self._database_service.get_optional_project(session, project_uid)
            if project is None:
                raise NotFoundError(f"Project {project_uid} not found")
            return self._get_migration(session, project).model

    def resolve(
        self,
        project_uid: UUID,
        attribute_issue_uid: UUID,
        attribute: AnyAttribute | None,
    ) -> AttributeMigrationIssue:
        """Resolve an attribute issue: a value on its attribute schema, or left
        empty. A dropped attribute is resolved by accepting it, without a value.

        Parameters
        ----------
        project_uid: UUID
            The uid of the project.
        attribute_issue_uid: UUID
            The uid of the attribute issue.
        attribute: AnyAttribute | None
            The value, or None to leave the attribute empty or accept it as
            dropped.

        Returns
        -------
        AttributeMigrationIssue
            The attribute issue, resolved.

        Raises
        ------
        NotFoundError
            If there is no such project, it has no migration, or the migration
            has no such attribute issue.
        NotAllowedActionError
            If the migration is not being curated, the value is not on the
            attribute schema of the attribute issue, or a value is given for a
            dropped attribute.
        """
        with self._database_service.get_session() as session:
            project = self._lock_project(session, project_uid)
            migration = self._get_migration(session, project)
            self._assert_migration_status(migration, MigrationStatus.CURATING)
            found = next(
                (
                    (object_, issue)
                    for object_ in migration.objects
                    for issue in object_.attribute_issues
                    if issue.uid == attribute_issue_uid
                ),
                None,
            )
            if found is None:
                raise NotFoundError(
                    f"The migration of project {project.uid} has no attribute "
                    f"issue {attribute_issue_uid}."
                )
            object_, issue = found
            if issue.dropped:
                if attribute is not None:
                    raise NotAllowedActionError(
                        f"Attribute issue {issue.uid} is of a dropped attribute, "
                        f"which is accepted without a value."
                    )
            else:
                tag, schema = ProjectMigrationPlanner.get_issue_attribute_schema(
                    self._schema_service.get_root(migration.target_root_schema_uid),
                    object_,
                    issue,
                )
                if attribute is not None and attribute.schema_uid != schema.uid:
                    raise NotAllowedActionError(
                        f"The value of {tag!r} must be on attribute schema "
                        f"{schema.uid}, not {attribute.schema_uid}."
                    )
            issue.resolve(attribute)
            migration.set_status(MigrationStatus.CURATING)
            session.flush()
            return issue.model

    def submit(self, project_uid: UUID) -> ProjectMigration:
        """Set a curated migration to be completed.

        Parameters
        ----------
        project_uid: UUID
            The uid of the project.

        Returns
        -------
        ProjectMigration
            The migration, being completed.

        Raises
        ------
        NotFoundError
            If there is no such project, or it has no migration.
        NotAllowedActionError
            If the migration is not being curated, or an attribute issue is
            not resolved, or a dropped attribute not accepted.
        """
        with self._database_service.get_session() as session:
            project = self._lock_project(session, project_uid)
            migration = self._get_migration(session, project)
            self._assert_migration_status(migration, MigrationStatus.CURATING)
            unresolved = sum(
                1
                for object_ in migration.objects
                for issue in object_.attribute_issues
                if issue.resolved_at is None
            )
            if unresolved:
                raise NotAllowedActionError(
                    f"The migration cannot be submitted: {unresolved} attribute "
                    f"issues are not resolved."
                )
            migration.set_status(MigrationStatus.COMPLETING)
            session.flush()
            return migration.model

    def resume_curating(self, project_uid: UUID) -> None:
        """Set a migration whose completion was not started back to being
        curated.

        Nothing is done where the migration is not being completed.

        Parameters
        ----------
        project_uid: UUID
            The uid of the project.

        Raises
        ------
        NotFoundError
            If there is no such project, or it has no migration.
        """
        with self._database_service.get_session() as session:
            project = self._lock_project(session, project_uid)
            migration = self._get_migration(session, project)
            if migration.status == MigrationStatus.COMPLETING:
                migration.set_status(MigrationStatus.CURATING)

    def complete(self, project_uid: UUID, session: Session | None = None) -> None:
        """Complete a submitted migration: run it again, put the resolved values
        at their tags, replace the attributes of every object, validate the
        project again, and set it back to the status it had.

        A migration is applied whole or not at all. Nothing is done where the
        project has no migration being completed.

        Parameters
        ----------
        project_uid: UUID
            The uid of the project.
        session: Session | None = None
            The session to complete it in, which the caller commits, or None
            for a session of its own.

        Raises
        ------
        NotFoundError
            If there is no such project.
        NotAllowedActionError
            If the project can no longer be migrated.
        MigrationError
            If the migration returns what it may not, or no longer what was
            planned.
        """
        with self._database_service.get_session(session) as session:
            project = self._lock_project(session, project_uid)
            migration = self._database_service.get_optional_project_migration(
                session, project.uid
            )
            if migration is None or migration.status != MigrationStatus.COMPLETING:
                self._logger.warning(
                    f"Project {project.uid} has no migration being completed."
                )
                return
            self.assert_can_migrate(project, session, started=True)
            planner = self._create_planner(project, migration)
            objects = self._migrate_objects(session, project, planner)
            search_items = self._migrate_search_items(session, project, planner)
            target_root = self._schema_service.get_root(
                migration.target_root_schema_uid
            )
            issues = {
                (
                    object_.object_uid,
                    ProjectMigrationPlanner.get_issue_attribute_schema(
                        target_root, object_, issue
                    )[0],
                ): issue
                for object_ in migration.objects
                for issue in object_.attribute_issues
                if not issue.dropped
            }
            dropped = {
                (object_.object_uid, issue.source_attribute_schema_uid)
                for object_ in migration.objects
                for issue in object_.attribute_issues
                if issue.dropped
            }
            planner.refuse_changed_plan(project.name, objects, issues.keys(), dropped)
            executor = ProjectMigrationExecutor(
                session,
                self._database_service,
                self._attribute_service,
                self._validation_service,
                self._review_service,
            )
            executor.write(
                project,
                migration.target_root_schema_uid,
                objects,
                search_items,
                issues,
            )
            project.status = migration.previous_project_status
            session.delete(migration)
            session.flush()
            executor.revalidate(project)
            self._logger.info(
                f"Project {project.uid} migrated to root schema "
                f"{project.root_schema_uid}."
            )

    def revert(self, project_uid: UUID) -> Project:
        """Remove the migration of a project and its plan, and set the project
        back to the status it had.

        Also for a migration that failed, or whose task was lost: nothing of
        the project is changed until the migration is completed.

        Parameters
        ----------
        project_uid: UUID
            The uid of the project.

        Returns
        -------
        Project
            The project, with the status it had.

        Raises
        ------
        NotFoundError
            If there is no such project, or it has no migration.
        """
        with self._database_service.get_session() as session:
            project = self._lock_project(session, project_uid)
            migration = self._get_migration(session, project)
            if project.status == ProjectStatus.MIGRATING:
                project.status = migration.previous_project_status
            session.delete(migration)
            session.flush()
            self._logger.info(f"Migration of project {project.uid} reverted.")
            return project.model

    def fail(self, project_uid: UUID, error: str) -> None:
        """Set the migration of a project being planned or completed as failed.

        Nothing is done where the project has no migration being planned or
        completed.

        Parameters
        ----------
        project_uid: UUID
            The uid of the project.
        error: str
            Why the migration failed.
        """
        with self._database_service.get_session() as session:
            migration = self._database_service.get_optional_project_migration(
                session, project_uid
            )
            if migration is not None and migration.status in (
                MigrationStatus.PLANNING,
                MigrationStatus.COMPLETING,
            ):
                migration.set_status(MigrationStatus.FAILED, error)

    def migrate_refusal(
        self,
        project: DatabaseProject,
        session: Session | None = None,
        started: bool = False,
    ) -> str | None:
        """Tell why a project cannot be migrated.

        A project is migrated only where its root has a migration, and not
        while deleted or, before the migration has started, being migrated. A
        project that has been exported cannot be migrated, as its exported
        metadata uses the schema it was exported with, nor one with images
        stored, or locked to be stored, nor one with batches being searched or
        processed.

        Parameters
        ----------
        project: DatabaseProject
            The project.
        session: Session | None = None
            The session to read the batches of the project in.
        started: bool = False
            Whether the migration has started. If it has, the project must have
            the status MIGRATING.

        Returns
        -------
        str | None
            Why the project cannot be migrated, or None where it can.
        """
        if self._schema_service.migration_of(project.root_schema_uid) is None:
            return self.NO_MIGRATION_REFUSAL
        if started:
            if project.status != ProjectStatus.MIGRATING:
                return self.NOT_MIGRATING_REFUSAL
        elif project.status in SchemaService.INACTIVE_STATUSES:
            return SchemaService.INACTIVE_STATUSES[project.status]
        if project.was_exported:
            return self.EXPORTED_REFUSAL
        with self._database_service.get_session(session) as session:
            if DatabaseService.has_stored_batches(session, project):
                return self.STORED_REFUSAL
            if DatabaseService.has_busy_batches(session, project):
                return self.BUSY_REFUSAL
        return None

    def assert_can_migrate(
        self,
        project: DatabaseProject,
        session: Session | None = None,
        started: bool = False,
    ) -> None:
        """Refuse migrating a project that cannot be, see `migrate_refusal`.

        Parameters
        ----------
        project: DatabaseProject
            The project, locked where it is to be migrated.
        session: Session | None = None
            The session to read the batches of the project in.
        started: bool = False
            Whether the migration has started.

        Raises
        ------
        NotAllowedActionError
            If the project cannot be migrated, with why.
        """
        reason = self.migrate_refusal(project, session, started)
        if reason is not None:
            raise NotAllowedActionError(f"The project cannot be migrated: {reason}.")

    def _lock_project(self, session: Session, project_uid: UUID) -> DatabaseProject:
        """Get a project, its row locked so that what is checked is what is
        changed.

        Parameters
        ----------
        session: Session
            The session to lock it in.
        project_uid: UUID
            The uid of the project.

        Returns
        -------
        DatabaseProject
            The project, locked.

        Raises
        ------
        NotFoundError
            If there is no such project.
        """
        project = self._database_service.get_optional_project_for_update(
            session, project_uid
        )
        if project is None:
            raise NotFoundError(f"Project {project_uid} not found")
        return project

    def _get_migration(
        self, session: Session, project: DatabaseProject
    ) -> DatabaseProjectMigration:
        """Get the migration of a project.

        Parameters
        ----------
        session: Session
            The session to get it in.
        project: DatabaseProject
            The project.

        Returns
        -------
        DatabaseProjectMigration
            The migration.

        Raises
        ------
        NotFoundError
            If the project has no migration.
        """
        try:
            return self._database_service.get_project_migration(session, project.uid)
        except NoResultFound as exception:
            raise NotFoundError(
                f"Project {project.uid} has no migration."
            ) from exception

    @staticmethod
    def _assert_migration_status(
        migration: DatabaseProjectMigration, status: MigrationStatus
    ) -> None:
        """Refuse a migration that does not have a status.

        Parameters
        ----------
        migration: DatabaseProjectMigration
            The migration.
        status: MigrationStatus
            The status it must have.

        Raises
        ------
        NotAllowedActionError
            If the migration has another status.
        """
        if migration.status != status:
            raise NotAllowedActionError(
                f"The migration is {migration.status.value}, not {status.value}."
            )

    def _create_planner(
        self, project: DatabaseProject, migration: DatabaseProjectMigration
    ) -> ProjectMigrationPlanner:
        """Create the planner of the migration of a project, from the root it
        is on to the target root of the migration.

        Parameters
        ----------
        project: DatabaseProject
            The project, on the source root.
        migration: DatabaseProjectMigration
            The migration of the project.

        Returns
        -------
        ProjectMigrationPlanner
            The planner, with the migration of the source root.

        Raises
        ------
        NotAllowedActionError
            If the source root has no migration.
        """
        schema_migration = self._schema_service.migration_of(project.root_schema_uid)
        if schema_migration is None:
            raise NotAllowedActionError(
                f"Project {project.name} is on root schema "
                f"{project.root_schema_uid}, which has no migration."
            )
        return ProjectMigrationPlanner(
            self._schema_service.get_root(project.root_schema_uid),
            self._schema_service.get_root(migration.target_root_schema_uid),
            schema_migration,
        )

    def _migrate_objects(
        self,
        session: Session,
        project: DatabaseProject,
        planner: ProjectMigrationPlanner,
    ) -> list[ObjectInMigration]:
        """Run the migration for the project, its dataset, and its items without
        saving them.

        Parameters
        ----------
        session: Session
            The session to read the project in.
        project: DatabaseProject
            The project, on the source root.
        planner: ProjectMigrationPlanner
            The planner of the migration.

        Returns
        -------
        list[ObjectInMigration]
            The project, the dataset, and the items, checked against the target
            root.

        Raises
        ------
        MigrationError
            If the migration returns what it may not.
        """
        dataset = self._database_service.get_dataset(session, project.dataset_uid)
        return planner.migrate_objects(
            [
                project.model,
                dataset.model,
                *(
                    item.model
                    for item in self._database_service.get_items_in_dataset(
                        session, dataset.uid, load_attributes=True
                    )
                ),
            ]
        )

    def _migrate_search_items(
        self,
        session: Session,
        project: DatabaseProject,
        planner: ProjectMigrationPlanner,
    ) -> list[SearchItemInMigration]:
        """Pair the search items of the batches of a project with the item
        schemas the migration moves them to.

        Parameters
        ----------
        session: Session
            The session to read the search items in.
        project: DatabaseProject
            The project, on the source root.
        planner: ProjectMigrationPlanner
            The planner of the migration.

        Returns
        -------
        list[SearchItemInMigration]
            The search items, with their target item schemas.

        Raises
        ------
        MigrationError
            If the migration moves a search item off the item schemas of its
            kind in the target root.
        """
        return planner.migrate_search_items(
            [
                row.model
                for batch in project.batches
                for row in self._database_service.get_metadata_search_items_in_batch(
                    session, batch.uid
                )
            ]
        )
