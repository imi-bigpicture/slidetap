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

import contextlib
import dataclasses
import logging
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from typing import ClassVar
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from slidetap.database import (
    DatabaseAttribute,
    DatabaseAttributeMigrationIssue,
    DatabaseDataset,
    DatabaseItem,
    DatabaseMapper,
    DatabaseMappingItem,
    DatabaseMetadataSearchItem,
    DatabaseProject,
    DatabaseProjectMigration,
    DatabaseUnmappedValue,
)
from slidetap.external_interfaces import SchemaMigration
from slidetap.external_interfaces.implementations.migration import (
    UnchangedAttributeMigrator,
)
from slidetap.model import (
    AnnotationSchema,
    AnyAttribute,
    AttributeMigrationIssue,
    AttributeSchema,
    Dataset,
    DatasetSchema,
    ImageSchema,
    Item,
    ItemSchema,
    MetadataSearchItem,
    MigrationError,
    MigrationStatus,
    NotAllowedActionError,
    NotFoundError,
    ObjectMigrationIssues,
    ObjectMigrationResult,
    ObservationSchema,
    Project,
    ProjectMigration,
    ProjectSchema,
    ProjectStatus,
    RootSchemaIndex,
    SampleSchema,
    UnresolvedAttributeMigration,
)
from slidetap.services.attribute_service import AttributeService
from slidetap.services.database_service import DatabaseService
from slidetap.services.mapper_service import MapperService
from slidetap.services.review_service import ReviewService
from slidetap.services.schema_service import SchemaService
from slidetap.services.validation_service import ValidationService
from slidetap.services.validators.attribute_validator import AttributeValidator

AnyObjectSchema = ProjectSchema | DatasetSchema | ItemSchema
"""The schema of what a migration is given: a project, a dataset, or an item."""


@dataclass(frozen=True)
class ObjectInMigration:
    """An object of the project, and what the migration returned for it."""

    source: Project | Dataset | Item
    """The object as it is on the source root."""

    target_schema: AnyObjectSchema
    """Its schema on the target root."""

    target_attributes: Mapping[str, AnyAttribute | UnresolvedAttributeMigration]
    """Its attributes on the target schema by tag, each migrated, or
    unresolved for the curator to resolve."""

    target_private_attributes: Mapping[str, AnyAttribute | UnresolvedAttributeMigration]
    """Its private attributes on the target schema, as `target_attributes`."""

    def unresolved(
        self,
    ) -> Iterator[tuple[str, UnresolvedAttributeMigration, AttributeSchema | None]]:
        """Iterate the unresolved attributes, public then private.

        Returns
        -------
        Iterator[tuple[str, UnresolvedAttributeMigration, AttributeSchema | None]]
            The tag and the unresolved attribute, with the attribute schema of
            the tag among the public or the private attributes of the target
            schema, as the attribute is, or None where it has none.
        """
        for attributes, schemas in (
            (self.target_attributes, self.target_schema.attributes),
            (self.target_private_attributes, self.target_schema.private_attributes),
        ):
            for tag, attribute in attributes.items():
                if isinstance(attribute, UnresolvedAttributeMigration):
                    yield tag, attribute, schemas.get(tag)


@dataclass(frozen=True)
class SearchItemInMigration:
    """A search item of the project, and the item schema the migration moves it
    to."""

    source: MetadataSearchItem
    """The search item as it is on the source root."""

    target_schema: ItemSchema
    """Its item schema on the target root."""


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

    The stored mappers are moved by `migrate_mappers()` to the schemas the
    migrations give their attributes.
    """

    ITEM_SCHEMA_KINDS = (SampleSchema, ImageSchema, AnnotationSchema, ObservationSchema)

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
        mapper_service: MapperService,
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
        mapper_service: MapperService
            For removing the mapping items a migration leaves without a target.
        """
        self._schema_service = schema_service
        self._database_service = database_service
        self._attribute_service = attribute_service
        self._validation_service = validation_service
        self._review_service = review_service
        self._mapper_service = mapper_service
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
            stale = self._get_optional(session, project.uid)
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
            return self._model(session, project, migration)

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
            migration = self._get_optional(session, project.uid)
            if migration is None or migration.status != MigrationStatus.PLANNING:
                self._logger.warning(
                    f"Project {project.uid} has no migration being planned."
                )
                return
            self.assert_can_migrate(project, session, started=True)
            objects, _ = self._run(session, project)
            target_root = self._schema_service.get_root(
                migration.target_root_schema_uid
            )
            for object_ in objects:
                migration.attribute_issues.extend(
                    self._attribute_issues(object_, target_root)
                )
            migration.set_status(MigrationStatus.CURATING)
            self._logger.info(
                f"Migration of project {project.uid} planned, with "
                f"{len(migration.attribute_issues)} attribute issues."
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
            return self._model(session, project, self._get(session, project.uid))

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
            migration = self._get(session, project.uid)
            self._assert_status(migration, MigrationStatus.CURATING)
            issue = next(
                (
                    issue
                    for issue in migration.attribute_issues
                    if issue.uid == attribute_issue_uid
                ),
                None,
            )
            if issue is None:
                raise NotFoundError(
                    f"The migration of project {project.uid} has no attribute "
                    f"issue {attribute_issue_uid}."
                )
            if issue.dropped:
                if attribute is not None:
                    raise NotAllowedActionError(
                        f"Attribute issue {issue.uid} is of a dropped attribute, "
                        f"which is accepted without a value."
                    )
            else:
                tag, schema = self._issue_attribute_schema(migration, issue)
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
            migration = self._get(session, project.uid)
            self._assert_status(migration, MigrationStatus.CURATING)
            unresolved = sum(
                1 for issue in migration.attribute_issues if issue.resolved_at is None
            )
            if unresolved:
                raise NotAllowedActionError(
                    f"The migration cannot be submitted: {unresolved} attribute "
                    f"issues are not resolved."
                )
            migration.set_status(MigrationStatus.COMPLETING)
            session.flush()
            return self._model(session, project, migration)

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
            migration = self._get(session, project.uid)
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
            migration = self._get_optional(session, project.uid)
            if migration is None or migration.status != MigrationStatus.COMPLETING:
                self._logger.warning(
                    f"Project {project.uid} has no migration being completed."
                )
                return
            self.assert_can_migrate(project, session, started=True)
            objects, search_items = self._run(session, project)
            issues = {
                (
                    issue.object_uid,
                    self._issue_attribute_schema(migration, issue)[0],
                ): issue
                for issue in migration.attribute_issues
                if not issue.dropped
            }
            dropped = {
                (issue.object_uid, issue.source_attribute_schema_uid)
                for issue in migration.attribute_issues
                if issue.dropped
            }
            self._assert_as_planned(project, objects, issues.keys(), dropped)
            dataset = self._database_service.get_dataset(session, project.dataset_uid)
            items: list[DatabaseItem] = []
            for object_ in objects:
                row = self._write(session, self._with_resolutions(object_, issues))
                if isinstance(row, DatabaseItem):
                    items.append(row)
            for search_item in search_items:
                row = session.get_one(
                    DatabaseMetadataSearchItem, search_item.source.uid
                )
                row.schema_uid = search_item.target_schema.uid
            project.root_schema_uid = migration.target_root_schema_uid
            project.status = migration.previous_project_status
            session.delete(migration)
            session.flush()
            self._validate(session, project, dataset, items)
            self._review_service.flag_invalid_review_units(dataset.uid, session=session)
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
            migration = self._get(session, project.uid)
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
            migration = session.scalars(
                select(DatabaseProjectMigration).where(
                    DatabaseProjectMigration.project_uid == project_uid
                )
            ).one_or_none()
            if migration is not None and migration.status in (
                MigrationStatus.PLANNING,
                MigrationStatus.COMPLETING,
            ):
                migration.set_status(MigrationStatus.FAILED, error)

    def migrate_mappers(self) -> None:
        """Migrate the mappers of the attributes that a schema migration gives
        another schema.

        Migrations are to the root of new projects only, so a mapper is
        migrated once at most, and running this again changes nothing.

        Raises
        ------
        ValueError
            If a migration fails on the attributes of a mapper, naming it.
        """
        migrations = self._schema_service.migrations
        with self._database_service.get_session() as session:
            for mapper in self._database_service.get_all_mappers(session):
                for source_uid, migration in migrations.items():
                    source = self._schema_service.get_root(source_uid)
                    if not source.has_attribute(mapper.attribute_schema_uid):
                        continue
                    try:
                        migrated = self._migrate_mapper(session, migration, mapper)
                    except Exception as exception:
                        raise ValueError(
                            f"Mapper '{mapper.name}' could not be migrated from "
                            f"root schema {source_uid} to "
                            f"{self._schema_service.default_root.uid}: {exception}"
                        ) from exception
                    if migrated:
                        break

    def _migrate_mapper(
        self, session: Session, migration: SchemaMigration, mapper: DatabaseMapper
    ) -> bool:
        """Migrate a mapper to the schemas a migration gives its attributes, and
        to the family of the root of new projects.

        The schemas are given by `SchemaMigration.migrate_attribute_schema`
        for the attribute schema of the mapper and its root attribute schema;
        a mapper whose schemas the migration gives no target, or the same ones,
        is left as it is. The mapper keeps its uid, name, groups, expressions,
        and hits, and each of its mapping items is migrated in place by
        `migrate_attribute`. A mapping item migrated to None, or to an
        attribute without an original value, is removed, and the attributes it
        mapped keep what they were mapped to.

        Parameters
        ----------
        session: Session
            The session to migrate it in.
        migration: SchemaMigration
            The migration from the root of the mapper.
        mapper: DatabaseMapper
            The mapper.

        Returns
        -------
        bool
            Whether the mapper was migrated.

        Raises
        ------
        ValueError
            If another mapper of its name is in the family it is migrated to.
        """
        try:
            attribute_schema = self._schema_service.get_any_attribute(
                mapper.attribute_schema_uid
            )
            root_attribute_schema = self._schema_service.get_any_attribute(
                mapper.root_attribute_schema_uid
            )
        except ValueError:
            return False
        target_attribute_schema = migration.migrate_attribute_schema(attribute_schema)
        target_root_attribute_schema = (
            target_attribute_schema
            if root_attribute_schema.uid == attribute_schema.uid
            else migration.migrate_attribute_schema(root_attribute_schema)
        )
        if target_attribute_schema is None or target_root_attribute_schema is None:
            return False
        if (target_attribute_schema.uid, target_root_attribute_schema.uid) == (
            mapper.attribute_schema_uid,
            mapper.root_attribute_schema_uid,
        ):
            # The same schema in both roots, which the mapper serves as it is.
            return False
        if self._database_service.get_mapper_for_schemas(
            session, target_attribute_schema.uid, target_root_attribute_schema.uid
        ):
            self._logger.warning(
                f"Mapper {mapper.name} is not migrated to attribute schema "
                f"{target_attribute_schema.uid}, which another mapper maps."
            )
            return False
        family_uid = self._schema_service.default_root.family_uid
        named = self._database_service.get_mapper_by_name(
            session, mapper.name, family_uid
        )
        if named is not None and named.uid != mapper.uid:
            raise ValueError(
                f"Mapper '{mapper.name}' cannot be migrated to family {family_uid}, "
                f"which has another mapper of that name."
            )
        removed: set[UUID] = set()
        for mapping in list(
            self._database_service.get_mappings_for_mapper(session, mapper.uid)
        ):
            attribute = migration.migrate_attribute(mapping.attribute)
            # A mapping maps to what its attribute was imported with, and one
            # whose value has no counterpart would map to nothing.
            if attribute is None or attribute.original_value is None:
                self._logger.warning(
                    f"Mapping {mapping.expression!r} of mapper {mapper.name} has no "
                    f"target, and is removed."
                )
                removed.add(mapping.uid)
                continue
            mapping.attribute = attribute
        if removed:
            self._mapper_service.forget_mapping_items(
                session, mapper.root_attribute_schema_uid, removed
            )
        mapper.attribute_schema_uid = target_attribute_schema.uid
        mapper.root_attribute_schema_uid = target_root_attribute_schema.uid
        mapper.family_uid = family_uid
        session.flush()
        self._logger.info(
            f"Moved mapper {mapper.name} to attribute schema "
            f"{target_attribute_schema.uid}."
        )
        return True

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
        project = session.get(DatabaseProject, project_uid, with_for_update=True)
        if project is None:
            raise NotFoundError(f"Project {project_uid} not found")
        return project

    def _get_optional(
        self, session: Session, project_uid: UUID
    ) -> DatabaseProjectMigration | None:
        """Get the migration of a project, if it has one.

        Parameters
        ----------
        session: Session
            The session to get it in.
        project_uid: UUID
            The uid of the project.

        Returns
        -------
        DatabaseProjectMigration | None
            The migration, or None where the project has none.
        """
        return session.scalars(
            select(DatabaseProjectMigration).where(
                DatabaseProjectMigration.project_uid == project_uid
            )
        ).one_or_none()

    def _get(self, session: Session, project_uid: UUID) -> DatabaseProjectMigration:
        """Get the migration of a project.

        Parameters
        ----------
        session: Session
            The session to get it in.
        project_uid: UUID
            The uid of the project.

        Returns
        -------
        DatabaseProjectMigration
            The migration.

        Raises
        ------
        NotFoundError
            If the project has no migration.
        """
        migration = self._get_optional(session, project_uid)
        if migration is None:
            raise NotFoundError(f"Project {project_uid} has no migration.")
        return migration

    @staticmethod
    def _assert_status(
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

    @classmethod
    def _assert_as_planned(
        cls,
        project: DatabaseProject,
        objects: Iterable[ObjectInMigration],
        planned_unresolved: Iterable[tuple[UUID, str]],
        planned_dropped: Iterable[tuple[UUID, UUID | None]],
    ) -> None:
        """Refuse a migration that no longer leaves unresolved or drops what
        the plan has attribute issues of.

        Parameters
        ----------
        project: DatabaseProject
            The project.
        objects: Iterable[ObjectInMigration]
            The objects of the project, as the migration returned them now.
        planned_unresolved: Iterable[tuple[UUID, str]]
            The uid of the object and the target tag of each attribute issue
            of the plan with a target.
        planned_dropped: Iterable[tuple[UUID, UUID | None]]
            The uid of the object and the source attribute schema uid of each
            dropped attribute of the plan.

        Raises
        ------
        MigrationError
            If the attributes left unresolved or dropped are not those of the
            plan.
        """
        objects = list(objects)
        now: set[tuple[UUID, str | UUID | None]] = {
            (object_.source.uid, tag)
            for object_ in objects
            for tag, _, _ in object_.unresolved()
        }
        now.update(
            (object_.source.uid, attribute.schema_uid)
            for object_ in objects
            for attribute in cls._dropped(object_)
        )
        planned: set[tuple[UUID, str | UUID | None]] = {
            *planned_unresolved,
            *planned_dropped,
        }
        if now != planned:
            raise MigrationError(
                f"The migration of project {project.name} no longer leaves "
                f"unresolved or drops what was planned: {len(now - planned)} "
                f"attributes are unresolved or dropped that are not in the plan, "
                f"and {len(planned - now)} in the plan are no longer. Revert "
                f"the migration and start it again."
            )

    def _run(
        self, session: Session, project: DatabaseProject
    ) -> tuple[list[ObjectInMigration], list[SearchItemInMigration]]:
        """Run the migration for every object of the project and for its search
        items, checking what it returns against the target root. Nothing is
        changed.

        Parameters
        ----------
        session: Session
            The session to read the project in.
        project: DatabaseProject
            The project, on the source root.

        Returns
        -------
        tuple[list[ObjectInMigration], list[SearchItemInMigration]]
            The project, the dataset, and the items, with every attribute that
            the migration left invalid, and that was valid before, unresolved;
            and the search items of the batches of the project.

        Raises
        ------
        NotAllowedActionError
            If the source root has no migration.
        MigrationError
            If the migration returns what it may not.
        """
        migration = self._migration_of(project)
        source_root = self._schema_service.get_root(project.root_schema_uid)
        target_root = self._schema_service.default_root
        dataset = self._database_service.get_dataset(session, project.dataset_uid)
        sources: list[Project | Dataset | Item] = [project.model, dataset.model]
        sources.extend(
            item.model
            for item in self._database_service.get_items_in_dataset(
                session, dataset.uid, load_attributes=True
            )
        )
        objects = [
            self._check(
                self._in_migration(
                    source, self._migrate(migration, source), source_root, target_root
                ),
                source_root,
                target_root,
            )
            for source in sources
        ]
        search_items: list[SearchItemInMigration] = []
        for batch in project.batches:
            for row in session.scalars(
                select(DatabaseMetadataSearchItem).where(
                    DatabaseMetadataSearchItem.batch_uid == batch.uid
                )
            ):
                search_item = row.model
                search_items.append(
                    SearchItemInMigration(
                        search_item,
                        self._target_item_schema(
                            source_root,
                            target_root,
                            f"search item {search_item.uid}",
                            search_item.schema_uid,
                            migration.migrate_item_schema(
                                source_root.get_item(search_item.schema_uid)
                            ).uid,
                        ),
                    )
                )
        return objects, search_items

    @staticmethod
    def _migrate(
        migration: SchemaMigration, source: Project | Dataset | Item
    ) -> ObjectMigrationResult:
        """Run the migration for an object, on a copy of it.

        Parameters
        ----------
        migration: SchemaMigration
            The migration of the source root.
        source: Project | Dataset | Item
            The object, on the source root.

        Returns
        -------
        ObjectMigrationResult
            What the migration returned for the object.
        """
        copy = source.model_copy(deep=True)
        if isinstance(copy, Project):
            return migration.migrate_project(copy)
        if isinstance(copy, Dataset):
            return migration.migrate_dataset(copy)
        return migration.migrate_item(copy)

    def _migration_of(self, project: DatabaseProject) -> SchemaMigration:
        """Get the migration of the source root of a project.

        Parameters
        ----------
        project: DatabaseProject
            The project.

        Returns
        -------
        SchemaMigration
            The migration from the source root of the project.

        Raises
        ------
        NotAllowedActionError
            If the source root has no migration.
        """
        migration = self._schema_service.migration_of(project.root_schema_uid)
        if migration is None:
            raise NotAllowedActionError(
                f"Project {project.name} is on root schema "
                f"{project.root_schema_uid}, which has no migration."
            )
        return migration

    def _in_migration(
        self,
        source: Project | Dataset | Item,
        migrated: ObjectMigrationResult,
        source_root: RootSchemaIndex,
        target_root: RootSchemaIndex,
    ) -> ObjectInMigration:
        """Pair an object with what the migration returned for it, on the
        target schema the migration put it on.

        Parameters
        ----------
        source: Project | Dataset | Item
            The object, on the source root.
        migrated: ObjectMigrationResult
            What the migration returned for the object.
        source_root: RootSchemaIndex
            The root the object is on.
        target_root: RootSchemaIndex
            The root the object is migrated to.

        Returns
        -------
        ObjectInMigration
            The object, with the target schema and what the migration returned.

        Raises
        ------
        MigrationError
            If the target schema is not the project or the dataset schema of
            the target root for the project or the dataset, or not an item
            schema of the target root of the same kind for an item.
        """
        if isinstance(source, Project | Dataset):
            target_schema: AnyObjectSchema = (
                target_root.project
                if isinstance(source, Project)
                else target_root.dataset
            )
            if migrated.schema_uid != target_schema.uid:
                raise MigrationError(
                    f"The migration put {source.uid} on schema "
                    f"{migrated.schema_uid}, not on {target_schema.uid} of the "
                    f"target root."
                )
        else:
            target_schema = self._target_item_schema(
                source_root,
                target_root,
                f"item {source.uid}",
                source.schema_uid,
                migrated.schema_uid,
            )
        return ObjectInMigration(
            source,
            target_schema,
            migrated.attributes,
            migrated.private_attributes,
        )

    def _target_item_schema(
        self,
        source_root: RootSchemaIndex,
        target_root: RootSchemaIndex,
        name: str,
        source_schema_uid: UUID,
        target_schema_uid: UUID,
    ) -> ItemSchema:
        """Get the item schema of the target root an item or a search item is
        migrated to, which must be of the kind of its source schema.

        Parameters
        ----------
        source_root: RootSchemaIndex
            The root the item or search item is on.
        target_root: RootSchemaIndex
            The root it is migrated to.
        name: str
            What it is, for the error.
        source_schema_uid: UUID
            The uid of its source schema.
        target_schema_uid: UUID
            The uid of the target schema the migration put it on.

        Returns
        -------
        ItemSchema
            The target schema.

        Raises
        ------
        MigrationError
            If the target root has no item schema of the uid, or one of
            another kind.
        """
        source_schema = source_root.items.get(source_schema_uid)
        target_schema = target_root.items.get(target_schema_uid)
        if target_schema is None or not any(
            isinstance(source_schema, kind) and isinstance(target_schema, kind)
            for kind in self.ITEM_SCHEMA_KINDS
        ):
            raise MigrationError(
                f"The migration put {name} on schema {target_schema_uid}, which "
                f"is not an item schema of the same kind in the target root."
            )
        return target_schema

    def _check(
        self,
        object_: ObjectInMigration,
        source_root: RootSchemaIndex,
        target_root: RootSchemaIndex,
    ) -> ObjectInMigration:
        """Refuse what the migration returned off the target schema, and leave
        unresolved what it left invalid that was valid.

        Parameters
        ----------
        object_: ObjectInMigration
            The object, as the migration returned it.
        source_root: RootSchemaIndex
            The root the object is on.
        target_root: RootSchemaIndex
            The root the object is migrated to.

        Returns
        -------
        ObjectInMigration
            The object, with every attribute that the migration left invalid,
            and that was valid before, unresolved.

        Raises
        ------
        MigrationError
            If an attribute is not the target schema's by tag, or an unresolved
            attribute is not a tag of the target schema, among the public or
            the private attributes as it is, or is proposed on another
            attribute schema.
        """
        uid, target_schema = object_.source.uid, object_.target_schema
        for attributes, schemas in (
            (object_.target_attributes, target_schema.attributes),
            (object_.target_private_attributes, target_schema.private_attributes),
        ):
            for tag, attribute in attributes.items():
                if isinstance(attribute, UnresolvedAttributeMigration):
                    continue
                self._check_attribute(uid, tag, attribute, schemas.get(tag))
        for tag, unresolved, attribute_schema in object_.unresolved():
            if attribute_schema is None:
                raise MigrationError(
                    f"The migration left {tag!r} of {uid} unresolved, which "
                    f"is not an attribute of the target schema."
                )
            if unresolved.proposed is not None:
                self._check_attribute(uid, tag, unresolved.proposed, attribute_schema)
        return self._with_invalidated(object_, source_root, target_root)

    def _with_invalidated(
        self,
        object_: ObjectInMigration,
        source_root: RootSchemaIndex,
        target_root: RootSchemaIndex,
    ) -> ObjectInMigration:
        """Leave unresolved every top-level attribute that the migration left
        invalid, and that was valid before: one newly required and without a
        value, or one whose value is not valid on the target schema. One that
        was invalid before is left as it is.

        Parameters
        ----------
        object_: ObjectInMigration
            The object, as the migration returned it.
        source_root: RootSchemaIndex
            The root the object is on.
        target_root: RootSchemaIndex
            The root the object is migrated to.

        Returns
        -------
        ObjectInMigration
            The object, with those attributes unresolved.
        """
        source_schema = self._object_schema(source_root, object_.source.schema_uid)
        attributes = dict(object_.target_attributes)
        for tag, target_attribute_schema in object_.target_schema.attributes.items():
            attribute = attributes.get(tag)
            if isinstance(attribute, UnresolvedAttributeMigration):
                continue
            if self._is_valid(attribute, target_attribute_schema):
                continue
            source_tag, original = self._original(object_.source, attribute, tag)
            source_attribute_schema = source_schema.attributes.get(source_tag)
            if source_attribute_schema is not None and not self._is_valid(
                original, source_attribute_schema
            ):
                continue
            attributes[tag] = UnresolvedAttributeMigration(
                original=original,
                proposed=attribute,
                problem=(
                    f"Required in {target_root.display_name}, has no value."
                    if attribute is None or attribute.value is None
                    else f"Not a valid value in {target_root.display_name}."
                ),
            )
        return dataclasses.replace(object_, target_attributes=attributes)

    @staticmethod
    def _original(
        source: Project | Dataset | Item, attribute: AnyAttribute | None, tag: str
    ) -> tuple[str, AnyAttribute | None]:
        """Get the attribute of the source object a migrated attribute was.

        Parameters
        ----------
        source: Project | Dataset | Item
            The object, on the source root.
        attribute: AnyAttribute | None
            The migrated attribute, or None where there is none.
        tag: str
            The target tag of the migrated attribute.

        Returns
        -------
        tuple[str, AnyAttribute | None]
            The source tag and the attribute of the same uid, else the tag and
            the attribute of the source object at it, None where it has none.
        """
        if attribute is not None:
            for source_tag, original in source.attributes.items():
                if original.uid == attribute.uid:
                    return source_tag, original
        return tag, source.attributes.get(tag)

    @staticmethod
    def _is_valid(attribute: AnyAttribute | None, schema: AttributeSchema) -> bool:
        """Check if an attribute is valid on an attribute schema.

        Parameters
        ----------
        attribute: AnyAttribute | None
            The attribute, or None where there is none.
        schema: AttributeSchema
            The attribute schema.

        Returns
        -------
        bool
            Whether the attribute is valid, or None is, as the schema is
            optional.
        """
        if attribute is None:
            return schema.optional
        return AttributeValidator.validate_attribute(
            attribute.model_copy(deep=True), schema
        )

    @staticmethod
    def _check_attribute(
        object_uid: UUID,
        tag: str,
        attribute: AnyAttribute,
        schema: AttributeSchema | None,
    ) -> AttributeSchema:
        """Refuse an attribute that is not on the attribute schema of its tag.

        Parameters
        ----------
        object_uid: UUID
            The uid of the object of the attribute, for the error.
        tag: str
            The target tag of the attribute.
        attribute: AnyAttribute
            The attribute.
        schema: AttributeSchema | None
            The attribute schema of the tag in the target schema, or None
            where it has none.

        Returns
        -------
        AttributeSchema
            The attribute schema of the tag.

        Raises
        ------
        MigrationError
            If the target schema has no attribute of the tag, or the attribute
            is on another attribute schema.
        """
        if schema is None or schema.uid != attribute.schema_uid:
            raise MigrationError(
                f"Attribute {attribute.uid} of {object_uid} is migrated to "
                f"schema {attribute.schema_uid} as {tag!r}, which is not an "
                f"attribute of the target schema."
            )
        return schema

    def _attribute_issues(
        self, object_: ObjectInMigration, target_root: RootSchemaIndex
    ) -> Iterable[DatabaseAttributeMigrationIssue]:
        """Make the attribute issues of what an object left unresolved, and of
        what it dropped.

        Parameters
        ----------
        object_: ObjectInMigration
            The object, checked.
        target_root: RootSchemaIndex
            The root the object is migrated to.

        Returns
        -------
        Iterable[DatabaseAttributeMigrationIssue]
            An attribute issue for each unresolved attribute and each dropped
            attribute, with the original given its display value.

        Raises
        ------
        MigrationError
            If an unresolved attribute is not a tag of the target schema.
        """
        for tag, unresolved, schema in object_.unresolved():
            original = None
            if unresolved.original is not None:
                original = unresolved.original.model_copy(deep=True)
                self._set_display_value(original)
            if schema is None:
                raise MigrationError(
                    f"The migration left {tag!r} of {object_.source.uid} "
                    f"unresolved, which is not an attribute of the target schema."
                )
            yield DatabaseAttributeMigrationIssue(
                object_.source.uid,
                object_.target_schema.uid,
                original.schema_uid if original is not None else None,
                schema.uid,
                original,
                unresolved.proposed,
                unresolved.problem,
            )
        for attribute in self._dropped(object_):
            original = attribute.model_copy(deep=True)
            self._set_display_value(original)
            _, display_name = self._source_attribute_names(original.schema_uid)
            value = original.display_value
            dropped = display_name if value is None else f"'{value}' of {display_name}"
            yield DatabaseAttributeMigrationIssue(
                object_.source.uid,
                object_.target_schema.uid,
                original.schema_uid,
                None,
                original,
                None,
                f"{dropped} is dropped: it has no place in {target_root.display_name}.",
            )

    @staticmethod
    def _migrated(
        attributes: Mapping[str, AnyAttribute | UnresolvedAttributeMigration],
    ) -> dict[str, AnyAttribute]:
        """Get the migrated attributes of a mapping, leaving out the unresolved.

        Parameters
        ----------
        attributes: Mapping[str, AnyAttribute | UnresolvedAttributeMigration]
            The attributes of an object on the target schema, by tag.

        Returns
        -------
        dict[str, AnyAttribute]
            The migrated attributes, by tag.
        """
        return {
            tag: attribute
            for tag, attribute in attributes.items()
            if not isinstance(attribute, UnresolvedAttributeMigration)
        }

    @classmethod
    def _dropped(cls, object_: ObjectInMigration) -> list[AnyAttribute]:
        """Get the dropped attributes of an object: those with a value that the
        migration neither converted nor left unresolved.

        Parameters
        ----------
        object_: ObjectInMigration
            The object, checked.

        Returns
        -------
        list[AnyAttribute]
            The dropped attributes of the source object.
        """
        kept = {
            attribute.uid
            for attribute in (
                *cls._migrated(object_.target_attributes).values(),
                *cls._migrated(object_.target_private_attributes).values(),
                *(
                    unresolved.original
                    for _, unresolved, _ in object_.unresolved()
                    if unresolved.original is not None
                ),
            )
        }
        return [
            attribute
            for attribute in (
                *object_.source.attributes.values(),
                *object_.source.private_attributes.values(),
            )
            if attribute.uid not in kept and attribute.value is not None
        ]

    @staticmethod
    def _with_resolutions(
        object_: ObjectInMigration,
        issues: Mapping[tuple[UUID, str], DatabaseAttributeMigrationIssue],
    ) -> ObjectInMigration:
        """Put the resolved values at their tags, and nothing at a tag left
        empty.

        A resolved value is given the uid of the attribute it resolves, as the
        migration gives a converted one, keeping the row of the attribute and
        its lock and read only flags.

        Parameters
        ----------
        object_: ObjectInMigration
            The object, checked.
        issues: Mapping[tuple[UUID, str], DatabaseAttributeMigrationIssue]
            The resolved attribute issues with a target, by object uid and
            target tag, with one for each unresolved attribute of the object.

        Returns
        -------
        ObjectInMigration
            The object, with the resolved values and nothing unresolved.
        """
        resolved_mappings: list[
            dict[str, AnyAttribute | UnresolvedAttributeMigration]
        ] = []
        for attributes in (
            object_.target_attributes,
            object_.target_private_attributes,
        ):
            resolved_attributes: dict[
                str, AnyAttribute | UnresolvedAttributeMigration
            ] = {}
            for tag, attribute in attributes.items():
                if not isinstance(attribute, UnresolvedAttributeMigration):
                    resolved_attributes[tag] = attribute
                    continue
                resolved = issues[(object_.source.uid, tag)].resolved
                if resolved is None:
                    continue
                replaced = attribute.original or attribute.proposed
                if replaced is not None:
                    resolved = resolved.model_copy(update={"uid": replaced.uid})
                resolved_attributes[tag] = resolved
            resolved_mappings.append(resolved_attributes)
        attributes, private_attributes = resolved_mappings
        return dataclasses.replace(
            object_,
            target_attributes=attributes,
            target_private_attributes=private_attributes,
        )

    def _write(
        self, session: Session, object_: ObjectInMigration
    ) -> DatabaseProject | DatabaseDataset | DatabaseItem:
        """Put an object on its target schema, and replace its attributes with
        the target ones.

        The old rows are deleted and the target attributes inserted, keeping
        their uids, and with them the locks and read only flags of the rows of
        the same uid. The only rows referring to attribute rows are unmapped
        values, which go with them and are recorded again for the new rows.

        Parameters
        ----------
        session: Session
            The session to write it in.
        object_: ObjectInMigration
            The object, with the resolved values and nothing unresolved.

        Returns
        -------
        DatabaseProject | DatabaseDataset | DatabaseItem
            The row of the object, written.

        Raises
        ------
        MigrationError
            If an attribute is not on the attribute schema of its tag.
        """
        row = self._row(session, object_.source)
        target_schema = object_.target_schema
        old_rows: list[DatabaseAttribute] = [
            *row.attributes,
            *row.private_attributes,
        ]
        flags = {old.uid: (old.read_only, old.locked) for old in old_rows}
        if old_rows:
            # Deleted with them by the database, but said here for a database
            # that does not enforce its foreign keys.
            session.execute(
                delete(DatabaseUnmappedValue).where(
                    DatabaseUnmappedValue.root_attribute_uid.in_(list(flags))
                )
            )
        row.attributes = set()
        row.private_attributes = set()
        session.flush()
        row.schema_uid = target_schema.uid
        row.attributes = self._add_attributes(
            session,
            row,
            self._migrated(object_.target_attributes),
            target_schema.attributes,
            flags,
        )
        row.private_attributes = self._add_attributes(
            session,
            row,
            self._migrated(object_.target_private_attributes),
            target_schema.private_attributes,
            flags,
        )
        return row

    def _row(
        self, session: Session, source: Project | Dataset | Item
    ) -> DatabaseProject | DatabaseDataset | DatabaseItem:
        """Get the row of an object.

        Parameters
        ----------
        session: Session
            The session to get it in.
        source: Project | Dataset | Item
            The object.

        Returns
        -------
        DatabaseProject | DatabaseDataset | DatabaseItem
            The row of the object.
        """
        if isinstance(source, Project):
            return self._database_service.get_project(session, source)
        if isinstance(source, Dataset):
            return self._database_service.get_dataset(session, source)
        return self._database_service.get_item(session, source)

    def _add_attributes(
        self,
        session: Session,
        row: DatabaseProject | DatabaseDataset | DatabaseItem,
        attributes: Mapping[str, AnyAttribute],
        schemas: Mapping[str, AttributeSchema],
        flags: Mapping[UUID, tuple[bool, bool]],
    ) -> set[DatabaseAttribute]:
        """Add the rows of the target attributes of an object.

        Parameters
        ----------
        session: Session
            The session to add them in.
        row: DatabaseProject | DatabaseDataset | DatabaseItem
            The row of the object.
        attributes: Mapping[str, AnyAttribute]
            The target attributes, by tag.
        schemas: Mapping[str, AttributeSchema]
            The attribute schemas of the target schema, by tag.
        flags: Mapping[UUID, tuple[bool, bool]]
            The read only and locked flags of the old rows, by uid.

        Returns
        -------
        set[DatabaseAttribute]
            The added rows.

        Raises
        ------
        MigrationError
            If an attribute is not on the attribute schema of its tag.
        """
        rows: set[DatabaseAttribute] = set()
        for tag, attribute in attributes.items():
            schema = self._check_attribute(row.uid, tag, attribute, schemas.get(tag))
            # Mapping items a mapper move removed are referred to by nothing.
            attribute = UnchangedAttributeMigrator.without_mapping_items(
                attribute,
                lambda uid: session.get(DatabaseMappingItem, uid) is None,
            )
            self._attribute_service.set_display_value(attribute)
            attribute_row = self._database_service.add_attribute(
                session, attribute, schema
            )
            attribute_row.rejected = attribute.rejected
            attribute_row.read_only, attribute_row.locked = flags.get(
                attribute.uid, (False, False)
            )
            rows.add(attribute_row)
        return rows

    def _validate(
        self,
        session: Session,
        project: DatabaseProject,
        dataset: DatabaseDataset,
        items: list[DatabaseItem],
    ) -> None:
        """Validate the whole project again, on the target root.

        Parameters
        ----------
        session: Session
            The session to validate it in.
        project: DatabaseProject
            The project.
        dataset: DatabaseDataset
            The dataset of the project.
        items: list[DatabaseItem]
            The items of the dataset.
        """
        self._validation_service.validate_project_attributes(project, session)
        self._validation_service.validate_dataset_attributes(dataset, session)
        for item in items:
            self._validation_service.validate_item(item, session)

    def _model(
        self,
        session: Session,
        project: DatabaseProject,
        migration: DatabaseProjectMigration,
    ) -> ProjectMigration:
        """Make the model of a migration, with its attribute issues grouped by
        object.

        Parameters
        ----------
        session: Session
            The session to read the identifiers of the objects in.
        project: DatabaseProject
            The project.
        migration: DatabaseProjectMigration
            The migration of the project.

        Returns
        -------
        ProjectMigration
            The migration, with its attribute issues by object: the project,
            the dataset, then the items by identifier.
        """
        objects: dict[UUID, list[AttributeMigrationIssue]] = {}
        for issue in migration.attribute_issues:
            objects.setdefault(issue.object_uid, []).append(issue.model)
        dataset = self._database_service.get_dataset(session, project.dataset_uid)
        identifiers = {project.uid: project.name, dataset.uid: dataset.name}
        item_uids = objects.keys() - identifiers.keys()
        if item_uids:
            identifiers.update(
                session.execute(
                    select(DatabaseItem.uid, DatabaseItem.identifier).where(
                        DatabaseItem.uid.in_(item_uids)
                    )
                )
                .tuples()
                .all()
            )
        order = [project.uid, dataset.uid]
        issues = sorted(
            (
                ObjectMigrationIssues(
                    uid=uid,
                    identifier=identifiers[uid],
                    target_schema_uid=attribute_issues[0].target_object_schema_uid,
                    attribute_issues=attribute_issues,
                )
                for uid, attribute_issues in objects.items()
            ),
            key=lambda object_: (
                order.index(object_.uid) if object_.uid in order else len(order),
                object_.identifier,
            ),
        )
        return migration.model.model_copy(update={"issues": issues})

    @staticmethod
    def _object_schema(root: RootSchemaIndex, schema_uid: UUID) -> AnyObjectSchema:
        """Get the project, dataset, or item schema of a uid in a root.

        Parameters
        ----------
        root: RootSchemaIndex
            The source or target root.
        schema_uid: UUID
            The uid of the schema.

        Returns
        -------
        AnyObjectSchema
            The schema.

        Raises
        ------
        KeyError
            If the root has no object schema of the uid.
        """
        if schema_uid == root.project.uid:
            return root.project
        if schema_uid == root.dataset.uid:
            return root.dataset
        return root.items[schema_uid]

    def _issue_attribute_schema(
        self,
        migration: DatabaseProjectMigration,
        issue: DatabaseAttributeMigrationIssue,
    ) -> tuple[str, AttributeSchema]:
        """Get the target tag and attribute schema of an attribute issue.

        Parameters
        ----------
        migration: DatabaseProjectMigration
            The migration.
        issue: DatabaseAttributeMigrationIssue
            An attribute issue of the migration with a target.

        Returns
        -------
        tuple[str, AttributeSchema]
            The tag and attribute schema in the target schema of the object, a
            public or else a private attribute.

        Raises
        ------
        MigrationError
            If the target schema has no attribute of the attribute schema of
            the attribute issue, or it has none.
        """
        target_root = self._schema_service.get_root(migration.target_root_schema_uid)
        target_schema = self._object_schema(target_root, issue.target_object_schema_uid)
        for tag, attribute_schema in (
            *target_schema.attributes.items(),
            *target_schema.private_attributes.items(),
        ):
            if attribute_schema.uid == issue.target_attribute_schema_uid:
                return tag, attribute_schema
        raise MigrationError(
            f"Attribute issue {issue.uid} is of attribute schema "
            f"{issue.target_attribute_schema_uid}, which is not an attribute of schema "
            f"{target_schema.uid}."
        )

    def _set_display_value(self, attribute: AnyAttribute) -> None:
        """Set the display value of an attribute of the source root, where its
        schema is known.

        Parameters
        ----------
        attribute: AnyAttribute
            The attribute, given its display value.
        """
        with contextlib.suppress(KeyError, ValueError):
            self._attribute_service.set_display_value(attribute)

    def _source_attribute_names(self, attribute_schema_uid: UUID) -> tuple[str, str]:
        """Get the tag and display name of an attribute schema of the source
        root.

        Parameters
        ----------
        attribute_schema_uid: UUID
            The uid of the attribute schema.

        Returns
        -------
        tuple[str, str]
            The tag and display name, or the uid for both where no root has
            the attribute schema.
        """
        try:
            schema = self._schema_service.get_any_attribute(attribute_schema_uid)
        except (KeyError, ValueError):
            return str(attribute_schema_uid), str(attribute_schema_uid)
        return schema.tag, schema.display_name
