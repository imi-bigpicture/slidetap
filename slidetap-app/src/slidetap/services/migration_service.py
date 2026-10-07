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

"""Moving projects from one root schema to another."""

import logging
from collections import Counter
from collections.abc import Mapping
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from slidetap.database import (
    DatabaseAttribute,
    DatabaseDataset,
    DatabaseItem,
    DatabaseMappingItem,
    DatabaseMetadataSearchItem,
    DatabaseProject,
    DatabaseUnmappedValue,
)
from slidetap.external_interfaces import (
    MigratedObject,
)
from slidetap.external_interfaces.attribute_migrator import AttributeMigrator
from slidetap.model import (
    AnnotationSchema,
    AnyAttribute,
    AttributeSchema,
    Dataset,
    DatasetSchema,
    ImageSchema,
    Item,
    ItemSchema,
    MigrationAttributeChange,
    MigrationError,
    MigrationReport,
    NotAllowedActionError,
    NotFoundError,
    ObservationSchema,
    Project,
    ProjectSchema,
    ProjectStatus,
    RootSchemaIndex,
    SampleSchema,
)
from slidetap.services.attribute_service import AttributeService
from slidetap.services.database_service import DatabaseService
from slidetap.services.review_service import ReviewService
from slidetap.services.schema_service import SchemaService
from slidetap.services.validation_service import ValidationService

AnyObjectSchema = ProjectSchema | DatasetSchema | ItemSchema
"""The schema of what a migration is given: a project, a dataset, or an item."""

_Written = tuple[
    DatabaseProject | DatabaseDataset | DatabaseItem, AnyObjectSchema, MigratedObject
]
"""An object as written by a migration, with its schema and what it was given."""


class MigrationService:
    """Moves projects from the previous root schema they are on to the root of
    new projects.

    Every object of a project is given to the migration from its root, which
    returns the schema and attributes it has on the target root. The
    attributes of the object are then replaced by those, in one transaction
    for the whole project, which is validated again on the target root.

    A dry run is the migration itself, rolled back: what it reports is what a
    migration leaves behind.
    """

    ITEM_SCHEMA_KINDS = (SampleSchema, ImageSchema, AnnotationSchema, ObservationSchema)

    def __init__(
        self,
        schema_service: SchemaService,
        database_service: DatabaseService,
        attribute_service: AttributeService,
        validation_service: ValidationService,
        review_service: ReviewService,
    ):
        self._schema_service = schema_service
        self._database_service = database_service
        self._attribute_service = attribute_service
        self._validation_service = validation_service
        self._review_service = review_service
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def dry_run(self, project_uid: UUID) -> MigrationReport:
        """What migrating the project would do: the migration, rolled back.

        Raises
        ------
        NotAllowedActionError
            If the project cannot be migrated, or not now.
        """
        with self._database_service.get_session(commit=False) as session:
            project = self._database_service.get_optional_project(session, project_uid)
            if project is None:
                raise NotFoundError(f"Project {project_uid} not found")
            self._schema_service.support_of(project, session).assert_can_migrate()
            try:
                return self._migrate(session, project, project.status)
            finally:
                session.rollback()

    def start(self, project_uid: UUID) -> tuple[Project, ProjectStatus]:
        """Set the project as migrating, for the migration to be run as a task.

        Nothing can be done with the project until the migration is done.

        Returns
        -------
        tuple[Project, ProjectStatus]
            The project, and the status it had, to go back to when the
            migration is done or fails.

        Raises
        ------
        NotAllowedActionError
            If the project cannot be migrated, or not now.
        """
        with self._database_service.get_session() as session:
            # Locked, so that two requests cannot both find it not migrating.
            project = session.get(DatabaseProject, project_uid, with_for_update=True)
            if project is None:
                raise NotFoundError(f"Project {project_uid} not found")
            self._schema_service.support_of(project, session).assert_can_migrate()
            previous = project.status
            project.status = ProjectStatus.MIGRATING
            session.commit()
            self._logger.info(f"Project {project.uid} set as migrating.")
            return project.model, previous

    def migrate(
        self,
        project_uid: UUID,
        previous_status: ProjectStatus,
        session: Session | None = None,
    ) -> MigrationReport | None:
        """Migrate a project set as migrating, validate it again, and set it
        back to the status it had before the migration.

        In the session given, which the caller commits: a migration is applied
        whole or not at all. What was dropped or is invalid is flagged for the
        curator, whatever the status.

        Parameters
        ----------
        project_uid: UUID
            The project to migrate.
        previous_status: ProjectStatus
            The status the project had before it was set as migrating, as
            `start()` returns it.
        session: Session | None = None
            The session to migrate in, which the caller commits.

        Returns
        -------
        MigrationReport | None
            What was done, or None where the project is not set as migrating,
            as it is no longer by the time this is run.
        """
        with self._database_service.get_session(session) as session:
            # Locked, so that what is checked is what is migrated.
            project = session.get(DatabaseProject, project_uid, with_for_update=True)
            if project is None:
                raise NotFoundError(f"Project {project_uid} not found")
            if project.status != ProjectStatus.MIGRATING:
                self._logger.warning(
                    f"Project {project.uid} is {project.status.name.lower()}, not "
                    f"migrating, and is not migrated."
                )
                return None
            self._schema_service.support_of(project, session).assert_can_migrate(
                started=True
            )
            report = self._migrate(session, project, previous_status)
            self._logger.info(
                f"Project {project.uid} migrated to root schema "
                f"{report.target_root_schema_uid}."
            )
            return report

    def revert_status(self, project_uid: UUID, status: ProjectStatus) -> None:
        """Set a project whose migration failed back to the status it had."""
        self.revert_status_in(self._database_service, project_uid, status)

    @staticmethod
    def revert_status_in(
        database_service: DatabaseService, project_uid: UUID, status: ProjectStatus
    ) -> None:
        """Set a project whose migration failed back to the status it had,
        with no more than the database: for where the migration service could
        not be created."""
        with database_service.get_session() as session:
            project = database_service.get_project(session, project_uid)
            if project.status == ProjectStatus.MIGRATING:
                project.status = status

    def reset(self, project_uid: UUID) -> Project:
        """Take a project out of migrating that no migration is going to finish,
        such as one whose task was lost, back into progress.

        An administrative action, for when a migration is known not to be
        running: the project row is locked while it is set, but a migration
        that is still to run would find the project no longer migrating, and
        skip it.

        A migration is applied whole or not at all, so the project is as it
        was before the migration, and in progress for it to be completed again.

        Raises
        ------
        NotAllowedActionError
            If the project is not migrating.
        """
        with self._database_service.get_session() as session:
            project = session.get(DatabaseProject, project_uid, with_for_update=True)
            if project is None:
                raise NotFoundError(f"Project {project_uid} not found")
            if project.status != ProjectStatus.MIGRATING:
                raise NotAllowedActionError(f"Project {project.name} is not migrating.")
            project.status = ProjectStatus.IN_PROGRESS
            self._logger.warning(f"Project {project.uid} reset from migrating.")
            return project.model

    def _migrate(
        self, session: Session, project: DatabaseProject, status: ProjectStatus
    ) -> MigrationReport:
        """Migrate every object of the project, validate the project on the
        target root, and report what was dropped and what is invalid.

        The project is given the status after: what was dropped or is invalid
        is for the curator to fill in, which review units holding something
        invalid are flagged for.
        """
        migration = self._schema_service.migration_of(project.root_schema_uid)
        if migration is None:
            raise NotAllowedActionError(
                f"Project {project.name} is on root schema "
                f"{project.root_schema_uid}, which has no migration."
            )
        source = self._schema_service.get_root(project.root_schema_uid)
        target = self._schema_service.default_root
        dropped: Counter[tuple[UUID, str]] = Counter()
        written: list[_Written] = []
        dataset = self._database_service.get_dataset(session, project.dataset_uid)
        project_model = project.model
        migrated = migration.migrate_project(project_model.model_copy(deep=True))
        written.append(
            self._write(
                session, project, project_model, migrated, target.project, dropped
            )
        )
        dataset_model = dataset.model
        migrated = migration.migrate_dataset(dataset_model.model_copy(deep=True))
        written.append(
            self._write(
                session, dataset, dataset_model, migrated, target.dataset, dropped
            )
        )
        items = list(
            self._database_service.get_items_in_dataset(
                session, dataset.uid, load_attributes=True
            )
        )
        for item in items:
            item_model = item.model
            migrated = migration.migrate_item(item_model.model_copy(deep=True))
            schema = self._target_item_schema(
                source, target, f"item {item.uid}", item.schema_uid, migrated.schema_uid
            )
            written.append(
                self._write(session, item, item_model, migrated, schema, dropped)
            )
        project.root_schema_uid = target.uid
        for batch in project.batches:
            for search_item in session.scalars(
                select(DatabaseMetadataSearchItem).where(
                    DatabaseMetadataSearchItem.batch_uid == batch.uid
                )
            ):
                search_item.schema_uid = self._target_item_schema(
                    source,
                    target,
                    f"search item {search_item.uid}",
                    search_item.schema_uid,
                    migration.migrate_search_item(search_item.model),
                ).uid
        project.status = status
        session.flush()
        self._validate(session, project, dataset, items)
        self._review_service.flag_invalid_review_units(dataset.uid, session=session)
        return self._report(project.uid, source, target, len(items), dropped, written)

    def _target_item_schema(
        self,
        source: RootSchemaIndex,
        target: RootSchemaIndex,
        name: str,
        source_schema_uid: UUID,
        target_schema_uid: UUID,
    ) -> ItemSchema:
        """The item schema of the target root an item or a search item, as
        named, is migrated to, which must be of the kind of the one it is on.

        Raises
        ------
        MigrationError
            If the target root has no item schema of the uid, or one of
            another kind.
        """
        source_schema = source.items.get(source_schema_uid)
        target_schema = target.items.get(target_schema_uid)
        if target_schema is None or not any(
            isinstance(source_schema, kind) and isinstance(target_schema, kind)
            for kind in self.ITEM_SCHEMA_KINDS
        ):
            raise MigrationError(
                f"The migration put {name} on schema {target_schema_uid}, which "
                f"is not an item schema of the same kind in the target root."
            )
        return target_schema

    def _write(
        self,
        session: Session,
        owner: DatabaseProject | DatabaseDataset | DatabaseItem,
        model: Project | Dataset | Item,
        migrated: MigratedObject,
        schema: AnyObjectSchema,
        dropped: Counter[tuple[UUID, str]],
    ) -> _Written:
        """Replace the attributes of an object with the migrated ones, counting
        the attributes with a value it leaves out.

        The old rows are deleted and the migrated attributes inserted, keeping
        their uids, and with them the locks and read only flags of the rows of
        the same uid. The only rows referring to attribute rows are unmapped
        values, which go with them and are recorded again for the new rows.
        """
        if migrated.schema_uid != schema.uid:
            raise MigrationError(
                f"The migration put {owner.uid} on schema {migrated.schema_uid}, "
                f"not on {schema.uid} of the target root."
            )
        old_rows: list[DatabaseAttribute] = [
            *owner.attributes,
            *owner.private_attributes,
        ]
        kept = {
            attribute.uid
            for attribute in (
                *migrated.attributes.values(),
                *migrated.private_attributes.values(),
            )
        }
        for tag, attribute in (
            *model.attributes.items(),
            *model.private_attributes.items(),
        ):
            if attribute.uid not in kept and attribute.value is not None:
                dropped[(attribute.schema_uid, tag)] += 1
        flags = {row.uid: (row.read_only, row.locked) for row in old_rows}
        if old_rows:
            # Deleted with them by the database, but said here for a database
            # that does not enforce its foreign keys.
            session.execute(
                delete(DatabaseUnmappedValue).where(
                    DatabaseUnmappedValue.root_attribute_uid.in_(list(flags))
                )
            )
        owner.attributes = set()
        owner.private_attributes = set()
        session.flush()
        owner.schema_uid = migrated.schema_uid
        owner.attributes = self._add_attributes(
            session, owner, migrated.attributes, schema.attributes, flags
        )
        owner.private_attributes = self._add_attributes(
            session,
            owner,
            migrated.private_attributes,
            schema.private_attributes,
            flags,
        )
        return owner, schema, migrated

    def _add_attributes(
        self,
        session: Session,
        owner: DatabaseProject | DatabaseDataset | DatabaseItem,
        attributes: Mapping[str, AnyAttribute],
        schemas: Mapping[str, AttributeSchema],
        flags: Mapping[UUID, tuple[bool, bool]],
    ) -> set[DatabaseAttribute]:
        rows: set[DatabaseAttribute] = set()
        for tag, attribute in attributes.items():
            schema = schemas.get(tag)
            if schema is None or schema.uid != attribute.schema_uid:
                raise MigrationError(
                    f"Attribute {attribute.uid} of {owner.uid} is migrated to "
                    f"schema {attribute.schema_uid} as {tag!r}, which is not an "
                    f"attribute of the target schema."
                )
            # Mapping items a mapper move removed are referred to by nothing.
            attribute = AttributeMigrator.without_mapping_items(
                attribute,
                lambda uid: session.get(DatabaseMappingItem, uid) is None,
            )
            self._attribute_service.set_display_value(attribute)
            row = self._database_service.add_attribute(session, attribute, schema)
            row.rejected = attribute.rejected
            row.read_only, row.locked = flags.get(attribute.uid, (False, False))
            rows.add(row)
        return rows

    def _validate(
        self,
        session: Session,
        project: DatabaseProject,
        dataset: DatabaseDataset,
        items: list[DatabaseItem],
    ) -> None:
        """Validate the whole project again, on its new root."""
        self._validation_service.validate_project_attributes(project, session)
        self._validation_service.validate_dataset_attributes(dataset, session)
        for item in items:
            self._validation_service.validate_item(item, session)

    def _report(
        self,
        project_uid: UUID,
        source: RootSchemaIndex,
        target: RootSchemaIndex,
        items: int,
        dropped: Counter[tuple[UUID, str]],
        written: list[_Written],
    ) -> MigrationReport:
        """What was dropped, and what is invalid on the target root.

        Invalid is what validation found invalid of the public attributes, and
        a required attribute, public or private, without a value. Private
        attributes are not validated, so their rows say nothing.
        """
        invalid: Counter[tuple[UUID, str]] = Counter()
        for owner, schema, migrated in written:
            for row in owner.attributes:
                if not row.valid:
                    invalid[(row.schema_uid, row.tag)] += 1
            for tag, attribute_schema in schema.attributes.items():
                if not attribute_schema.optional and tag not in migrated.attributes:
                    invalid[(attribute_schema.uid, tag)] += 1
            for tag, attribute_schema in schema.private_attributes.items():
                attribute = migrated.private_attributes.get(tag)
                if not attribute_schema.optional and (
                    attribute is None or attribute.value is None
                ):
                    invalid[(attribute_schema.uid, tag)] += 1
        changes = {
            key: MigrationAttributeChange(
                attribute_schema_uid=key[0],
                tag=key[1],
                display_name=self._display_name(*key),
                dropped=dropped[key],
                invalid=invalid[key],
            )
            for key in dropped.keys() | invalid.keys()
        }
        return MigrationReport(
            project_uid=project_uid,
            source_root_schema_uid=source.uid,
            target_root_schema_uid=target.uid,
            target_root_schema_name=target.display_name,
            items=items,
            attributes=sorted(
                changes.values(), key=lambda change: (change.display_name, change.tag)
            ),
        )

    def _display_name(self, schema_uid: UUID, tag: str) -> str:
        try:
            return self._schema_service.get_any_attribute(schema_uid).display_name
        except ValueError:
            return tag
