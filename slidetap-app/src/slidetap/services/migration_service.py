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
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
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
    DatabaseSchemaMigration,
    DatabaseSchemaMigrationIssue,
    DatabaseUnmappedValue,
    StoredDroppedAttribute,
)
from slidetap.external_interfaces import MigratedObject, SchemaMigration
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
    MigrationDecision,
    MigrationDroppedAttribute,
    MigrationError,
    MigrationIssue,
    MigrationObject,
    MigrationObjectKind,
    MigrationState,
    NotAllowedActionError,
    NotFoundError,
    ObservationSchema,
    Project,
    ProjectMigration,
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

_SearchItems = list[tuple[DatabaseMetadataSearchItem, ItemSchema]]
"""The search items of a project, with the item schema each is moved to."""


@dataclass(frozen=True)
class _Migrated:
    """An object of a project, as the migration returned it."""

    owner: DatabaseProject | DatabaseDataset | DatabaseItem
    kind: MigrationObjectKind
    model: Project | Dataset | Item
    schema: AnyObjectSchema
    """The schema of the target root it is migrated to."""

    migrated: MigratedObject


class MigrationService:
    """Moves projects from the previous root schema they are on to the root of
    new projects, in steps.

    Started, the project is locked as migrating, and the migration planned in
    a task: run for every object without saving, with what it could not
    convert stored as issues. The curator decides each issue and submits,
    which completes the migration in a task, or aborts. Completing runs the
    migration again, puts the decided values at their tags, and replaces the
    attributes of every object, in one transaction for the whole project,
    which is validated again on the target root.
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

    def start(self, project_uid: UUID) -> ProjectMigration:
        """Set the project as migrating, with a migration to be planned.

        Raises
        ------
        NotAllowedActionError
            If the project cannot be migrated, or not now.
        """
        with self._database_service.get_session() as session:
            project = self._lock_project(session, project_uid)
            self._schema_service.support_of(project, session).assert_can_migrate()
            stale = self._get_optional(session, project.uid)
            if stale is not None:
                session.delete(stale)
                session.flush()
            migration = DatabaseSchemaMigration(
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
        store what it could not convert as issues, and what it dropped.

        Raises
        ------
        MigrationError
            If the migration returns what it may not.
        """
        with self._database_service.get_session() as session:
            project = self._lock_project(session, project_uid)
            migration = self._get_optional(session, project.uid)
            if migration is None or migration.state != MigrationState.PLANNING:
                self._logger.warning(
                    f"Project {project.uid} has no migration being planned."
                )
                return
            self._schema_service.support_of(project, session).assert_can_migrate(
                started=True
            )
            migrated, _ = self._run(session, project)
            dropped: list[StoredDroppedAttribute] = []
            for object_ in migrated:
                migration.issues.extend(self._issues(object_))
                dropped.extend(self._dropped(object_))
            migration.dropped_attributes = dropped
            migration.set_state(MigrationState.CURATING)
            self._logger.info(
                f"Migration of project {project.uid} planned, with "
                f"{len(migration.issues)} issues."
            )

    def get(self, project_uid: UUID) -> ProjectMigration:
        """The migration of a project, with its plan.

        Raises
        ------
        NotFoundError
            If the project has no migration.
        """
        with self._database_service.get_session(commit=False) as session:
            project = self._database_service.get_optional_project(session, project_uid)
            if project is None:
                raise NotFoundError(f"Project {project_uid} not found")
            return self._model(session, project, self._get(session, project.uid))

    def decide(
        self, project_uid: UUID, issue_uid: UUID, decision: MigrationDecision
    ) -> MigrationIssue:
        """Decide an issue: a value on the attribute schema of the issue, or
        left empty.

        Raises
        ------
        NotFoundError
            If the project has no migration, or no such issue.
        NotAllowedActionError
            If the migration is not being curated, or the value is not on the
            attribute schema of the issue.
        """
        with self._database_service.get_session() as session:
            project = self._lock_project(session, project_uid)
            migration = self._get(session, project.uid)
            self._assert_state(migration, MigrationState.CURATING)
            issue = next(
                (issue for issue in migration.issues if issue.uid == issue_uid), None
            )
            if issue is None:
                raise NotFoundError(
                    f"The migration of project {project.uid} has no issue {issue_uid}."
                )
            schema = self._issue_attribute_schema(migration, issue)
            if (
                decision.attribute is not None
                and decision.attribute.schema_uid != schema.uid
            ):
                raise NotAllowedActionError(
                    f"The value of {issue.tag!r} must be on attribute schema "
                    f"{schema.uid}, not {decision.attribute.schema_uid}."
                )
            issue.decide(decision.attribute)
            migration.set_state(MigrationState.CURATING)
            session.flush()
            return self._issue_model(migration, issue)

    def submit(self, project_uid: UUID) -> ProjectMigration:
        """Set a curated migration to be completed.

        Raises
        ------
        NotAllowedActionError
            If the migration is not being curated, or an issue is undecided.
        """
        with self._database_service.get_session() as session:
            project = self._lock_project(session, project_uid)
            migration = self._get(session, project.uid)
            self._assert_state(migration, MigrationState.CURATING)
            undecided = sum(1 for issue in migration.issues if not issue.decided)
            if undecided:
                raise NotAllowedActionError(
                    f"The migration cannot be submitted: {undecided} issues are "
                    f"undecided."
                )
            migration.set_state(MigrationState.COMPLETING)
            session.flush()
            return self._model(session, project, migration)

    def resume_curating(self, project_uid: UUID) -> None:
        """Set a migration whose completion was not started back to being
        curated."""
        with self._database_service.get_session() as session:
            project = self._lock_project(session, project_uid)
            migration = self._get(session, project.uid)
            if migration.state == MigrationState.COMPLETING:
                migration.set_state(MigrationState.CURATING)

    def complete(self, project_uid: UUID, session: Session | None = None) -> None:
        """Complete a submitted migration: run it again, put the decided values
        at their tags, replace the attributes of every object, validate the
        project again, and set it back to the status it had.

        In the session given, which the caller commits: a migration is applied
        whole or not at all.

        Raises
        ------
        MigrationError
            If the migration returns what it may not, or no longer what was
            planned.
        """
        with self._database_service.get_session(session) as session:
            project = self._lock_project(session, project_uid)
            migration = self._get_optional(session, project.uid)
            if migration is None or migration.state != MigrationState.COMPLETING:
                self._logger.warning(
                    f"Project {project.uid} has no migration being completed."
                )
                return
            self._schema_service.support_of(project, session).assert_can_migrate(
                started=True
            )
            migrated, search_items = self._run(session, project)
            issues = {
                (issue.object_uid, issue.tag): issue for issue in migration.issues
            }
            self._assert_as_planned(project, migrated, issues.keys())
            dataset = self._database_service.get_dataset(session, project.dataset_uid)
            items: list[DatabaseItem] = []
            for object_ in migrated:
                self._write(session, object_, self._with_decisions(object_, issues))
                if isinstance(object_.owner, DatabaseItem):
                    items.append(object_.owner)
            for search_item, schema in search_items:
                search_item.schema_uid = schema.uid
            project.root_schema_uid = migration.target_root_schema_uid
            project.status = migration.previous_status
            session.delete(migration)
            session.flush()
            self._validate(session, project, dataset, items)
            self._review_service.flag_invalid_review_units(dataset.uid, session=session)
            self._logger.info(
                f"Project {project.uid} migrated to root schema "
                f"{project.root_schema_uid}."
            )

    def abort(self, project_uid: UUID) -> Project:
        """Remove the migration of a project and its plan, and set the project
        back to the status it had.

        Also for a migration that failed, or whose task was lost: nothing of
        the project is changed until the migration is completed.

        Raises
        ------
        NotFoundError
            If the project has no migration.
        """
        with self._database_service.get_session() as session:
            project = self._lock_project(session, project_uid)
            migration = self._get(session, project.uid)
            if project.status == ProjectStatus.MIGRATING:
                project.status = migration.previous_status
            session.delete(migration)
            session.flush()
            self._logger.info(f"Migration of project {project.uid} aborted.")
            return project.model

    @staticmethod
    def fail_in(
        database_service: DatabaseService, project_uid: UUID, error: str
    ) -> None:
        """Set the migration of a project being planned or completed as failed,
        with no more than the database: for where the migration service could
        not be created."""
        with database_service.get_session() as session:
            migration = session.scalars(
                select(DatabaseSchemaMigration).where(
                    DatabaseSchemaMigration.project_uid == project_uid
                )
            ).one_or_none()
            if migration is not None and migration.state in (
                MigrationState.PLANNING,
                MigrationState.COMPLETING,
            ):
                migration.set_state(MigrationState.FAILED, error)

    def _lock_project(self, session: Session, project_uid: UUID) -> DatabaseProject:
        """The project, its row locked so that what is checked is what is
        changed."""
        project = session.get(DatabaseProject, project_uid, with_for_update=True)
        if project is None:
            raise NotFoundError(f"Project {project_uid} not found")
        return project

    def _get_optional(
        self, session: Session, project_uid: UUID
    ) -> DatabaseSchemaMigration | None:
        return session.scalars(
            select(DatabaseSchemaMigration).where(
                DatabaseSchemaMigration.project_uid == project_uid
            )
        ).one_or_none()

    def _get(self, session: Session, project_uid: UUID) -> DatabaseSchemaMigration:
        migration = self._get_optional(session, project_uid)
        if migration is None:
            raise NotFoundError(f"Project {project_uid} has no migration.")
        return migration

    @staticmethod
    def _assert_state(
        migration: DatabaseSchemaMigration, state: MigrationState
    ) -> None:
        if migration.state != state:
            raise NotAllowedActionError(
                f"The migration is {migration.state.value}, not {state.value}."
            )

    @staticmethod
    def _assert_as_planned(
        project: DatabaseProject,
        migrated: list[_Migrated],
        planned: Iterable[tuple[UUID, str]],
    ) -> None:
        """Refuse a migration that no longer leaves unresolved what the plan
        has issues of."""
        unresolved = {
            (object_.owner.uid, tag)
            for object_ in migrated
            for tag in object_.migrated.unresolved
        }
        planned = set(planned)
        if unresolved != planned:
            raise MigrationError(
                f"The migration of project {project.name} no longer leaves "
                f"unresolved what was planned: {len(unresolved - planned)} "
                f"attributes are unresolved that are not in the plan, and "
                f"{len(planned - unresolved)} in the plan are no longer. Abort "
                f"the migration and start it again."
            )

    def _run(
        self, session: Session, project: DatabaseProject
    ) -> tuple[list[_Migrated], _SearchItems]:
        """Run the migration for every object of the project and for its search
        items, checking what it returns against the target root. Nothing is
        changed.

        Raises
        ------
        MigrationError
            If the migration returns what it may not.
        """
        migration = self._migration_of(project)
        source = self._schema_service.get_root(project.root_schema_uid)
        target = self._schema_service.default_root
        dataset = self._database_service.get_dataset(session, project.dataset_uid)
        project_model = project.model
        dataset_model = dataset.model
        migrated = [
            self._check(
                _Migrated(
                    project,
                    MigrationObjectKind.PROJECT,
                    project_model,
                    target.project,
                    migration.migrate_project(project_model.model_copy(deep=True)),
                )
            ),
            self._check(
                _Migrated(
                    dataset,
                    MigrationObjectKind.DATASET,
                    dataset_model,
                    target.dataset,
                    migration.migrate_dataset(dataset_model.model_copy(deep=True)),
                )
            ),
        ]
        for item in self._database_service.get_items_in_dataset(
            session, dataset.uid, load_attributes=True
        ):
            item_model = item.model
            migrated_item = migration.migrate_item(item_model.model_copy(deep=True))
            schema = self._target_item_schema(
                source,
                target,
                f"item {item.uid}",
                item.schema_uid,
                migrated_item.schema_uid,
            )
            migrated.append(
                self._check(
                    _Migrated(
                        item,
                        MigrationObjectKind.ITEM,
                        item_model,
                        schema,
                        migrated_item,
                    )
                )
            )
        search_items = [
            (
                search_item,
                self._target_item_schema(
                    source,
                    target,
                    f"search item {search_item.uid}",
                    search_item.schema_uid,
                    migration.migrate_search_item(search_item.model),
                ),
            )
            for batch in project.batches
            for search_item in session.scalars(
                select(DatabaseMetadataSearchItem).where(
                    DatabaseMetadataSearchItem.batch_uid == batch.uid
                )
            )
        ]
        return migrated, search_items

    def _migration_of(self, project: DatabaseProject) -> SchemaMigration:
        migration = self._schema_service.migration_of(project.root_schema_uid)
        if migration is None:
            raise NotAllowedActionError(
                f"Project {project.name} is on root schema "
                f"{project.root_schema_uid}, which has no migration."
            )
        return migration

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

    def _check(self, object_: _Migrated) -> _Migrated:
        """Refuse what the migration returned off the target schema.

        Raises
        ------
        MigrationError
            If the object is put on another schema, an attribute is not the
            target schema's by tag, or an unresolved attribute is not a tag of
            the target schema, is also converted, or is proposed on another
            attribute schema.
        """
        owner, schema, migrated = object_.owner, object_.schema, object_.migrated
        if migrated.schema_uid != schema.uid:
            raise MigrationError(
                f"The migration put {owner.uid} on schema {migrated.schema_uid}, "
                f"not on {schema.uid} of the target root."
            )
        for attributes, schemas in (
            (migrated.attributes, schema.attributes),
            (migrated.private_attributes, schema.private_attributes),
        ):
            for tag, attribute in attributes.items():
                self._check_attribute(owner.uid, tag, attribute, schemas.get(tag))
        for tag, unresolved in migrated.unresolved.items():
            attribute_schema = self._attribute_schema(schema, tag)
            if attribute_schema is None:
                raise MigrationError(
                    f"The migration left {tag!r} of {owner.uid} unresolved, which "
                    f"is not an attribute of the target schema."
                )
            if tag in migrated.attributes or tag in migrated.private_attributes:
                raise MigrationError(
                    f"The migration both converted and left unresolved {tag!r} of "
                    f"{owner.uid}."
                )
            if unresolved.proposed is not None:
                self._check_attribute(
                    owner.uid, tag, unresolved.proposed, attribute_schema
                )
        return object_

    @staticmethod
    def _check_attribute(
        owner_uid: UUID,
        tag: str,
        attribute: AnyAttribute,
        schema: AttributeSchema | None,
    ) -> AttributeSchema:
        """The attribute schema of the tag, which the attribute must be on."""
        if schema is None or schema.uid != attribute.schema_uid:
            raise MigrationError(
                f"Attribute {attribute.uid} of {owner_uid} is migrated to "
                f"schema {attribute.schema_uid} as {tag!r}, which is not an "
                f"attribute of the target schema."
            )
        return schema

    @staticmethod
    def _attribute_schema(schema: AnyObjectSchema, tag: str) -> AttributeSchema | None:
        """The attribute schema of a tag of an object schema, a public or else a
        private attribute."""
        return schema.attributes.get(tag) or schema.private_attributes.get(tag)

    def _issues(self, object_: _Migrated) -> Iterable[DatabaseSchemaMigrationIssue]:
        for tag, unresolved in object_.migrated.unresolved.items():
            original = unresolved.original.model_copy(deep=True)
            self._set_display_value(original)
            yield DatabaseSchemaMigrationIssue(
                object_.owner.uid,
                object_.kind,
                object_.schema.uid,
                tag,
                original,
                unresolved.proposed,
                unresolved.reason,
            )

    def _dropped(self, object_: _Migrated) -> Iterable[StoredDroppedAttribute]:
        """The attributes with a value of the object that the migration neither
        converted nor left unresolved."""
        migrated = object_.migrated
        kept = {
            attribute.uid
            for attribute in (
                *migrated.attributes.values(),
                *migrated.private_attributes.values(),
                *(unresolved.original for unresolved in migrated.unresolved.values()),
            )
        }
        for tag, attribute in (
            *object_.model.attributes.items(),
            *object_.model.private_attributes.items(),
        ):
            if attribute.uid in kept or attribute.value is None:
                continue
            attribute = attribute.model_copy(deep=True)
            self._set_display_value(attribute)
            yield StoredDroppedAttribute(
                object_uid=object_.owner.uid,
                object_kind=object_.kind,
                object_schema_uid=object_.schema.uid,
                tag=tag,
                display_name=self._display_name(attribute.schema_uid, tag),
                display_value=attribute.display_value,
            )

    @staticmethod
    def _with_decisions(
        object_: _Migrated,
        issues: Mapping[tuple[UUID, str], DatabaseSchemaMigrationIssue],
    ) -> MigratedObject:
        """The migrated object with the decided values at their tags, and
        nothing at a tag left empty."""
        migrated = object_.migrated
        attributes = dict(migrated.attributes)
        private_attributes = dict(migrated.private_attributes)
        for tag in migrated.unresolved:
            decision = issues[(object_.owner.uid, tag)].decision
            if decision is None:
                continue
            if tag in object_.schema.attributes:
                attributes[tag] = decision
            else:
                private_attributes[tag] = decision
        return dataclasses.replace(
            migrated,
            attributes=attributes,
            private_attributes=private_attributes,
            unresolved={},
        )

    def _write(
        self, session: Session, object_: _Migrated, migrated: MigratedObject
    ) -> None:
        """Replace the attributes of an object with the migrated ones.

        The old rows are deleted and the migrated attributes inserted, keeping
        their uids, and with them the locks and read only flags of the rows of
        the same uid. The only rows referring to attribute rows are unmapped
        values, which go with them and are recorded again for the new rows.
        """
        owner, schema = object_.owner, object_.schema
        old_rows: list[DatabaseAttribute] = [
            *owner.attributes,
            *owner.private_attributes,
        ]
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
            schema = self._check_attribute(owner.uid, tag, attribute, schemas.get(tag))
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

    def _model(
        self,
        session: Session,
        project: DatabaseProject,
        migration: DatabaseSchemaMigration,
    ) -> ProjectMigration:
        """The migration, with its issues and dropped attributes by object."""
        target = self._schema_service.get_root(migration.target_root_schema_uid)
        objects: dict[UUID, MigrationObject] = {}
        for issue in migration.issues:
            self._object(
                objects,
                target,
                issue.object_uid,
                issue.object_kind,
                issue.object_schema_uid,
            ).issues.append(self._issue_model(migration, issue))
        for dropped in migration.dropped_attributes:
            self._object(
                objects,
                target,
                dropped.object_uid,
                dropped.object_kind,
                dropped.object_schema_uid,
            ).dropped.append(
                MigrationDroppedAttribute(
                    tag=dropped.tag,
                    display_name=dropped.display_name,
                    display_value=dropped.display_value,
                )
            )
        identifiers = self._identifiers(session, project, objects.values())
        kinds = list(MigrationObjectKind)
        ordered = sorted(
            (
                object_.model_copy(update={"identifier": identifiers[object_.uid]})
                for object_ in objects.values()
            ),
            key=lambda object_: (kinds.index(object_.kind), object_.identifier),
        )
        return ProjectMigration(
            project_uid=project.uid,
            source_root_schema_uid=migration.source_root_schema_uid,
            target_root_schema_uid=migration.target_root_schema_uid,
            target_root_schema_name=target.display_name,
            previous_status=migration.previous_status,
            state=migration.state,
            error=migration.error,
            created=migration.created,
            updated=migration.updated,
            objects=ordered,
            issues=len(migration.issues),
            decided=sum(1 for issue in migration.issues if issue.decided),
        )

    def _object(
        self,
        objects: dict[UUID, MigrationObject],
        target: RootSchemaIndex,
        uid: UUID,
        kind: MigrationObjectKind,
        schema_uid: UUID,
    ) -> MigrationObject:
        """The object of the uid in the objects, added where it is not."""
        if uid not in objects:
            objects[uid] = MigrationObject(
                uid=uid,
                kind=kind,
                identifier="",
                schema_uid=schema_uid,
                schema_display_name=self._object_schema(
                    target, kind, schema_uid
                ).display_name,
            )
        return objects[uid]

    @staticmethod
    def _object_schema(
        target: RootSchemaIndex, kind: MigrationObjectKind, schema_uid: UUID
    ) -> AnyObjectSchema:
        if kind == MigrationObjectKind.PROJECT:
            return target.project
        if kind == MigrationObjectKind.DATASET:
            return target.dataset
        return target.items[schema_uid]

    def _identifiers(
        self,
        session: Session,
        project: DatabaseProject,
        objects: Iterable[MigrationObject],
    ) -> dict[UUID, str]:
        """The names of the project and dataset, and the identifiers of the
        items, by uid."""
        dataset = self._database_service.get_dataset(session, project.dataset_uid)
        identifiers = {project.uid: project.name, dataset.uid: dataset.name}
        item_uids = [
            object_.uid
            for object_ in objects
            if object_.kind == MigrationObjectKind.ITEM
        ]
        if item_uids:
            for uid, identifier in session.execute(
                select(DatabaseItem.uid, DatabaseItem.identifier).where(
                    DatabaseItem.uid.in_(item_uids)
                )
            ).all():
                identifiers[uid] = identifier
        return identifiers

    def _issue_attribute_schema(
        self, migration: DatabaseSchemaMigration, issue: DatabaseSchemaMigrationIssue
    ) -> AttributeSchema:
        """The attribute schema of the tag of an issue in the target root."""
        target = self._schema_service.get_root(migration.target_root_schema_uid)
        schema = self._object_schema(target, issue.object_kind, issue.object_schema_uid)
        attribute_schema = self._attribute_schema(schema, issue.tag)
        if attribute_schema is None:
            raise MigrationError(
                f"Issue {issue.uid} is of {issue.tag!r}, which is not an attribute "
                f"of schema {schema.uid}."
            )
        return attribute_schema

    def _issue_model(
        self, migration: DatabaseSchemaMigration, issue: DatabaseSchemaMigrationIssue
    ) -> MigrationIssue:
        schema = self._issue_attribute_schema(migration, issue)
        return MigrationIssue(
            uid=issue.uid,
            tag=issue.tag,
            attribute_schema_uid=schema.uid,
            display_name=schema.display_name,
            original=issue.original,
            proposed=issue.proposed,
            reason=issue.reason,
            decided=issue.decided,
            left_empty=issue.left_empty,
            decision=issue.decision,
        )

    def _set_display_value(self, attribute: AnyAttribute) -> None:
        """Set the display value of an attribute of the source root, where its
        schema is known."""
        with contextlib.suppress(KeyError, ValueError):
            self._attribute_service.set_display_value(attribute)

    def _display_name(self, schema_uid: UUID, tag: str) -> str:
        try:
            return self._schema_service.get_any_attribute(schema_uid).display_name
        except (KeyError, ValueError):
            return tag
