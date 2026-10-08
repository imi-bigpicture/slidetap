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
    Dataset,
    Item,
    MetadataSearchItem,
    MigrationStatus,
    NotAllowedActionError,
    NotFoundError,
    Project,
    ProjectMigration,
    ProjectStatus,
)
from slidetap.services.database_service import DatabaseService
from slidetap.services.migration.project_migration_executor import (
    ProjectMigrationExecutor,
)
from slidetap.services.migration.project_migration_planner import (
    ProjectMigrationPlanner,
)
from slidetap.services.schema_service import SchemaService


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

    Planning and completing run the migration with the
    `ProjectMigrationPlanner`, and completing writes it with the
    `ProjectMigrationExecutor`.
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
        planner: ProjectMigrationPlanner,
        executor: ProjectMigrationExecutor,
    ):
        """Create the migration service.

        Parameters
        ----------
        schema_service: SchemaService
            For the roots, their migrations, and whether a project can be
            changed.
        database_service: DatabaseService
            For the sessions and the rows of the project.
        planner: ProjectMigrationPlanner
            For running the migration without saving it.
        executor: ProjectMigrationExecutor
            For writing a completed migration.
        """
        self._schema_service = schema_service
        self._database_service = database_service
        self._planner = planner
        self._executor = executor
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
            database_project = self._lock_project(session, project_uid)
            self.assert_can_migrate(database_project, session)
            stale_database_migration = (
                self._database_service.get_optional_project_migration(
                    session, database_project.uid
                )
            )
            if stale_database_migration is not None:
                session.delete(stale_database_migration)
                session.flush()
            database_migration = DatabaseProjectMigration(
                database_project.uid,
                database_project.root_schema_uid,
                self._schema_service.default_root.uid,
                database_project.status,
            )
            session.add(database_migration)
            database_project.status = ProjectStatus.MIGRATING
            session.flush()
            self._logger.info(f"Project {database_project.uid} set as migrating.")
            return database_migration.model

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
            database_project = self._lock_project(session, project_uid)
            database_migration = self._database_service.get_optional_project_migration(
                session, database_project.uid
            )
            if (
                database_migration is None
                or database_migration.status != MigrationStatus.PLANNING
            ):
                self._logger.warning(
                    f"Project {database_project.uid} has no migration being planned."
                )
                return
            self.assert_can_migrate(database_project, session, started=True)
            # The search items are planned too, as one the migration cannot
            # move would fail the completion.
            plan = self._planner.plan(
                database_project.root_schema_uid,
                database_migration.target_root_schema_uid,
                self._get_objects(session, database_project),
                self._get_search_items(session, database_project),
            )
            for object_ in sorted(plan.objects, key=lambda object_: object_.order):
                database_issues = plan.attribute_issues[object_.source.uid]
                if database_issues:
                    database_migration.objects.append(
                        DatabaseMigrationObject(
                            object_.source.uid,
                            object_.target_schema.uid,
                            object_.identifier,
                            len(database_migration.objects),
                            database_issues,
                        )
                    )
            database_migration.set_status(MigrationStatus.CURATING)
            count = sum(
                len(database_object.attribute_issues)
                for database_object in database_migration.objects
            )
            self._logger.info(
                f"Migration of project {database_project.uid} planned, with {count} "
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
            database_project = self._database_service.get_optional_project(
                session, project_uid
            )
            if database_project is None:
                raise NotFoundError(f"Project {project_uid} not found")
            return self._get_migration(session, database_project).model

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
            database_project = self._lock_project(session, project_uid)
            database_migration = self._get_migration(session, database_project)
            self._assert_migration_status(database_migration, MigrationStatus.CURATING)
            found = next(
                (
                    (database_object, database_issue)
                    for database_object in database_migration.objects
                    for database_issue in database_object.attribute_issues
                    if database_issue.uid == attribute_issue_uid
                ),
                None,
            )
            if found is None:
                raise NotFoundError(
                    f"The migration of project {database_project.uid} has no "
                    f"attribute issue {attribute_issue_uid}."
                )
            database_object, database_issue = found
            if database_issue.target_attribute_schema_uid is None:
                if attribute is not None:
                    raise NotAllowedActionError(
                        f"Attribute issue {database_issue.uid} is of a dropped "
                        f"attribute, which is accepted without a value."
                    )
            else:
                target_root = self._schema_service.get_root(
                    database_migration.target_root_schema_uid
                )
                tag, schema = target_root.get_entity_attribute_schema(
                    database_object.target_object_schema_uid,
                    database_issue.target_attribute_schema_uid,
                )
                if attribute is not None and attribute.schema_uid != schema.uid:
                    raise NotAllowedActionError(
                        f"The value of {tag!r} must be on attribute schema "
                        f"{schema.uid}, not {attribute.schema_uid}."
                    )
            database_issue.resolve(attribute)
            database_migration.set_status(MigrationStatus.CURATING)
            session.flush()
            return database_issue.model

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
            database_project = self._lock_project(session, project_uid)
            database_migration = self._get_migration(session, database_project)
            self._assert_migration_status(database_migration, MigrationStatus.CURATING)
            unresolved = sum(
                1
                for database_object in database_migration.objects
                for database_issue in database_object.attribute_issues
                if database_issue.resolved_at is None
            )
            if unresolved:
                raise NotAllowedActionError(
                    f"The migration cannot be submitted: {unresolved} attribute "
                    f"issues are not resolved."
                )
            database_migration.set_status(MigrationStatus.COMPLETING)
            session.flush()
            return database_migration.model

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
            database_project = self._lock_project(session, project_uid)
            database_migration = self._get_migration(session, database_project)
            if database_migration.status == MigrationStatus.COMPLETING:
                database_migration.set_status(MigrationStatus.CURATING)

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
            database_project = self._lock_project(session, project_uid)
            database_migration = self._database_service.get_optional_project_migration(
                session, database_project.uid
            )
            if (
                database_migration is None
                or database_migration.status != MigrationStatus.COMPLETING
            ):
                self._logger.warning(
                    f"Project {database_project.uid} has no migration being completed."
                )
                return
            self.assert_can_migrate(database_project, session, started=True)
            plan = self._planner.plan(
                database_project.root_schema_uid,
                database_migration.target_root_schema_uid,
                self._get_objects(session, database_project),
                self._get_search_items(session, database_project),
            )
            self._planner.refuse_changed_plan(
                plan, database_project.name, database_migration.objects
            )
            resolutions = {
                (
                    database_object.object_uid,
                    database_issue.target_attribute_schema_uid,
                ): database_issue
                for database_object in database_migration.objects
                for database_issue in database_object.attribute_issues
                if database_issue.target_attribute_schema_uid is not None
            }
            self._executor.execute(session, database_project, plan, resolutions)
            database_project.status = database_migration.previous_project_status
            session.delete(database_migration)
            session.flush()
            self._executor.revalidate(session, database_project)
            self._logger.info(
                f"Project {database_project.uid} migrated to root schema "
                f"{database_project.root_schema_uid}."
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
            database_project = self._lock_project(session, project_uid)
            database_migration = self._get_migration(session, database_project)
            if database_project.status == ProjectStatus.MIGRATING:
                database_project.status = database_migration.previous_project_status
            session.delete(database_migration)
            session.flush()
            self._logger.info(f"Migration of project {database_project.uid} reverted.")
            return database_project.model

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
            database_migration = self._database_service.get_optional_project_migration(
                session, project_uid
            )
            if database_migration is not None and database_migration.status in (
                MigrationStatus.PLANNING,
                MigrationStatus.COMPLETING,
            ):
                database_migration.set_status(MigrationStatus.FAILED, error)

    def migrate_refusal(
        self,
        database_project: DatabaseProject,
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
        database_project: DatabaseProject
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
        if self._schema_service.migration_of(database_project.root_schema_uid) is None:
            return self.NO_MIGRATION_REFUSAL
        if started:
            if database_project.status != ProjectStatus.MIGRATING:
                return self.NOT_MIGRATING_REFUSAL
        elif database_project.status in SchemaService.INACTIVE_STATUSES:
            return SchemaService.INACTIVE_STATUSES[database_project.status]
        if database_project.was_exported:
            return self.EXPORTED_REFUSAL
        with self._database_service.get_session(session) as session:
            if DatabaseService.has_stored_batches(session, database_project):
                return self.STORED_REFUSAL
            if DatabaseService.has_busy_batches(session, database_project):
                return self.BUSY_REFUSAL
        return None

    def assert_can_migrate(
        self,
        database_project: DatabaseProject,
        session: Session | None = None,
        started: bool = False,
    ) -> None:
        """Refuse migrating a project that cannot be, see `migrate_refusal`.

        Parameters
        ----------
        database_project: DatabaseProject
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
        reason = self.migrate_refusal(database_project, session, started)
        if reason is not None:
            raise NotAllowedActionError(f"The project cannot be migrated: {reason}.")

    def _lock_project(self, session: Session, project_uid: UUID) -> DatabaseProject:
        """Get a project, locked so that what is checked is what is changed.

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
        database_project = self._database_service.get_optional_project_for_update(
            session, project_uid
        )
        if database_project is None:
            raise NotFoundError(f"Project {project_uid} not found")
        return database_project

    def _get_migration(
        self, session: Session, database_project: DatabaseProject
    ) -> DatabaseProjectMigration:
        """Get the migration of a project.

        Parameters
        ----------
        session: Session
            The session to get it in.
        database_project: DatabaseProject
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
            return self._database_service.get_project_migration(
                session, database_project.uid
            )
        except NoResultFound as exception:
            raise NotFoundError(
                f"Project {database_project.uid} has no migration."
            ) from exception

    @staticmethod
    def _assert_migration_status(
        database_migration: DatabaseProjectMigration, status: MigrationStatus
    ) -> None:
        """Refuse a migration that does not have a status.

        Parameters
        ----------
        database_migration: DatabaseProjectMigration
            The migration.
        status: MigrationStatus
            The status it must have.

        Raises
        ------
        NotAllowedActionError
            If the migration has another status.
        """
        if database_migration.status != status:
            raise NotAllowedActionError(
                f"The migration is {database_migration.status.value}, not "
                f"{status.value}."
            )

    def _get_objects(
        self, session: Session, database_project: DatabaseProject
    ) -> list[Project | Dataset | Item]:
        """Get the project, its dataset, and its items, with their attributes.

        Parameters
        ----------
        session: Session
            The session to read the project in.
        database_project: DatabaseProject
            The project.

        Returns
        -------
        list[Project | Dataset | Item]
            The project, the dataset, and the items.
        """
        database_dataset = self._database_service.get_dataset(
            session, database_project.dataset_uid
        )
        return [
            database_project.model,
            database_dataset.model,
            *(
                database_item.model
                for database_item in self._database_service.get_items_in_dataset(
                    session, database_dataset.uid, load_attributes=True
                )
            ),
        ]

    def _get_search_items(
        self, session: Session, database_project: DatabaseProject
    ) -> list[MetadataSearchItem]:
        """Get the search items of the batches of a project.

        Parameters
        ----------
        session: Session
            The session to read the search items in.
        database_project: DatabaseProject
            The project.

        Returns
        -------
        list[MetadataSearchItem]
            The search items.
        """
        return [
            database_search_item.model
            for database_batch in database_project.batches
            for database_search_item in (
                self._database_service.get_metadata_search_items_in_batch(
                    session, database_batch.uid
                )
            )
        ]
