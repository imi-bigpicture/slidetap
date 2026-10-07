#    Copyright 2024 SECTRA AB
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

"""Service for accessing schemas."""

import logging
from collections import Counter
from collections.abc import Mapping, Sequence
from functools import cached_property, partial
from itertools import chain
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from slidetap.database import (
    DatabaseAttribute,
    DatabaseBatch,
    DatabaseDataset,
    DatabaseItem,
    DatabaseProject,
)
from slidetap.external_interfaces.schema import SchemaInterface
from slidetap.external_interfaces.schema_migration import (
    SchemaMigration,
    SchemaMigrationInterface,
)
from slidetap.model import (
    AttributeSchema,
    BatchActivity,
    NotFoundError,
    Project,
    RootSchemaIndex,
    RootSchemaSupport,
)
from slidetap.services.database_service import DatabaseService


class SchemaService:
    """Schema service should be used to interface with schemas.

    Holds every root schema the application provides: the root of new
    projects, whose projects can be changed, and the previous roots, whose
    projects are view only. Which of them a project uses is stated by the
    project, and every operation on the project looks up its item schemas
    within that root, and every change to it is refused where the root is view
    only. Attribute schemas are looked up across roots, as an attribute schema
    uid means one definition wherever it is used.
    """

    def __init__(
        self,
        schema_interface: SchemaInterface,
        database_service: DatabaseService,
        schema_migration_interface: SchemaMigrationInterface | None = None,
    ):
        """Create a schema service, asking the plugin for its roots and its
        migrations once.

        Parameters
        ----------
        schema_interface: SchemaInterface
            The plugin's schema interface: its `root()` is the root of new
            projects, and its `previous_roots()` are view only.
        database_service: DatabaseService
            Where the projects are, which have to be on a provided root.
        schema_migration_interface: SchemaMigrationInterface | None = None
            The plugin's schema migrations, of the projects on the roots, if
            it has any.

        Raises
        ------
        ValueError
            If the roots or the migrations cannot be used, see `_validate()`.
        """
        self._database_service = database_service
        self._default_root = RootSchemaIndex(schema_interface.root(), is_default=True)
        self._provided = [
            self._default_root,
            *(
                RootSchemaIndex(schema, is_default=False)
                for schema in schema_interface.previous_roots()
            ),
        ]
        self._roots: dict[UUID, RootSchemaIndex] = {
            root.uid: root for root in self._provided
        }
        self._migration_list: list[SchemaMigration] = (
            list(schema_migration_interface.migrations)
            if schema_migration_interface is not None
            else []
        )
        self._migrations: dict[UUID, SchemaMigration] = {
            migration.source_root_uid: migration for migration in self._migration_list
        }
        self._validate()

    @property
    def migrations(self) -> Sequence[SchemaMigration]:
        """The migrations of the projects on the roots, one from a root at most."""
        return list(self._migrations.values())

    def migration_of(self, root_schema_uid: UUID) -> SchemaMigration | None:
        """The migration of the projects on a root, if there is one."""
        return self._migrations.get(root_schema_uid)

    @property
    def default_root(self) -> RootSchemaIndex:
        """The root of new projects."""
        return self._default_root

    @property
    def roots(self) -> Mapping[UUID, RootSchemaIndex]:
        """Every root the application provides, by uid."""
        return self._roots

    def get_root(self, root_schema_uid: UUID) -> RootSchemaIndex:
        """The root of this uid.

        Raises
        ------
        NotFoundError
            If the application does not provide a root of the uid.
        """
        root = self._roots.get(root_schema_uid)
        if root is None:
            raise NotFoundError(f"Root schema {root_schema_uid} not found.")
        return root

    def root_of(
        self,
        subject: Project
        | DatabaseProject
        | DatabaseDataset
        | DatabaseBatch
        | DatabaseItem,
        session: Session | None = None,
    ) -> RootSchemaIndex:
        """The root of the project something belongs to.

        The session is the one to look up in what the subject does not hold
        yet, such as the dataset of an item just added.

        Raises
        ------
        ValueError
            If the subject is a dataset, or of a dataset, without a project.
        """
        return self.get_root(self._project_of(subject, session).root_schema_uid)

    def root_of_dataset(
        self, dataset: DatabaseDataset | UUID, session: Session | None = None
    ) -> RootSchemaIndex:
        """The root of the project a dataset belongs to, the dataset given
        by its uid or as it is.

        Raises
        ------
        ValueError
            If the dataset has no project.
        """
        if isinstance(dataset, DatabaseDataset):
            return self.root_of(dataset, session)
        with self._database_service.get_session(session) as session:
            root_schema_uid = session.scalar(
                select(DatabaseProject.root_schema_uid).where(
                    DatabaseProject.dataset_uid == dataset
                )
            )
        if root_schema_uid is None:
            raise ValueError(f"Dataset {dataset} has no project.")
        return self.get_root(root_schema_uid)

    def support_of(
        self,
        subject: Project
        | DatabaseProject
        | DatabaseDataset
        | DatabaseBatch
        | DatabaseItem,
        session: Session | None = None,
    ) -> RootSchemaSupport:
        """What can be done with the project something belongs to: by its
        root and its state.

        The session is the one to look up in what the subject does not hold
        yet, such as the dataset of an item just added.

        Raises
        ------
        ValueError
            If the subject is a dataset, or of a dataset, without a project.
        """
        project = self._project_of(subject, session)
        root = self.get_root(project.root_schema_uid)
        has_migration = project.root_schema_uid in self._migrations
        # Read only where it is asked for, as it queries the batches.
        activity = (
            partial(self._batch_activity, project.uid, session)
            if has_migration
            else None
        )
        return RootSchemaSupport(
            root.uid,
            root.display_name,
            editable=root.is_default,
            status=project.status,
            exported=project.exported is not None,
            has_migration=has_migration,
            activity=activity,
        )

    def _batch_activity(
        self, project_uid: UUID, session: Session | None
    ) -> BatchActivity:
        """What the batches of a project are doing, read in the session given."""
        with self._database_service.get_session(session) as session:
            return DatabaseService.batch_activity(
                session, self._database_service.get_project(session, project_uid)
            )

    def support_of_attribute(
        self, attribute: DatabaseAttribute, session: Session | None = None
    ) -> RootSchemaSupport | None:
        """What can be done with the project an attribute row belongs to, None
        for one that belongs to no item, project, or dataset.

        Looks its owner up in the session given: for one attribute, as many of
        a project are better given its root schema support.
        """
        with self._database_service.get_session(session) as session:
            return self._support_of_owner(attribute, session)

    def _support_of_owner(
        self, attribute: DatabaseAttribute, session: Session
    ) -> RootSchemaSupport | None:
        item_uid = attribute.attribute_item_uid or attribute.private_attribute_item_uid
        project_uid = (
            attribute.attribute_project_uid or attribute.private_attribute_project_uid
        )
        dataset_uid = (
            attribute.attribute_dataset_uid or attribute.private_attribute_dataset_uid
        )
        if item_uid is not None:
            owner = session.get(DatabaseItem, item_uid)
        elif project_uid is not None:
            owner = session.get(DatabaseProject, project_uid)
        elif dataset_uid is not None:
            owner = session.get(DatabaseDataset, dataset_uid)
        else:
            return None
        return self.support_of(owner, session) if owner is not None else None

    def _project_of(
        self,
        subject: Project
        | DatabaseProject
        | DatabaseDataset
        | DatabaseBatch
        | DatabaseItem,
        session: Session | None,
    ) -> Project | DatabaseProject:
        if isinstance(subject, (Project, DatabaseProject)):
            return subject
        if isinstance(subject, DatabaseBatch):
            return subject.project
        if isinstance(subject, DatabaseDataset):
            project = subject.project
            dataset_uid = subject.uid
        elif subject.dataset is not None:
            project = subject.dataset.project
            dataset_uid = subject.dataset_uid
        else:
            # An item just added has its dataset uid but not yet its dataset,
            # which is then read from the session given. It is normally there
            # already, so this does not query mid-import.
            with self._database_service.get_session(session) as session:
                database_project = session.scalar(
                    select(DatabaseProject).where(
                        DatabaseProject.dataset_uid == subject.dataset_uid
                    )
                )
                project = (
                    database_project.model if database_project is not None else None
                )
            dataset_uid = subject.dataset_uid
        if project is None:
            raise ValueError(f"Dataset {dataset_uid} has no project.")
        return project

    def family_of_attribute(self, attribute_schema_uid: UUID) -> UUID | None:
        """The family of the roots an attribute schema is in, None for one no
        provided root has."""
        for root in self._roots.values():
            if root.has_attribute(attribute_schema_uid):
                return root.family_uid
        return None

    def get_attribute(self, attribute_schema_uid: UUID) -> AttributeSchema:
        return self._attributes[attribute_schema_uid]

    def get_attribute_by_name(
        self, attribute_name: str, root_schema_uid: UUID | None = None
    ) -> AttributeSchema:
        """An attribute schema by name, within a root.

        Names are only unique within a root, so the root is given; without it,
        the root of new projects.
        """
        return (
            self.get_root(root_schema_uid)
            if root_schema_uid is not None
            else self.default_root
        ).get_attribute_by_name(attribute_name)

    def get_private_attribute(self, attribute_schema_uid: UUID) -> AttributeSchema:
        return self._private_attributes[attribute_schema_uid]

    def has_attribute(self, attribute_schema_uid: UUID) -> bool:
        """Whether a provided root has an attribute of this uid.

        Uids are regenerated with the model they are declared in, so an
        attribute that is stored somewhere but is not here is one the provided
        roots no longer have, under that uid or at all.
        """
        return (
            attribute_schema_uid in self._attributes
            or attribute_schema_uid in self._private_attributes
        )

    def get_any_attribute(self, attribute_schema_uid: UUID) -> AttributeSchema:
        """The attribute schema of this uid, a public or a private attribute,
        in whichever root defines it.

        Raises
        ------
        ValueError
            If no provided root has an attribute schema of the uid.
        """
        if attribute_schema_uid in self._attributes:
            return self._attributes[attribute_schema_uid]
        if attribute_schema_uid in self._private_attributes:
            return self._private_attributes[attribute_schema_uid]
        raise ValueError(f"Attribute schema with UID {attribute_schema_uid} not found.")

    @cached_property
    def _attributes(self) -> dict[UUID, AttributeSchema]:
        """Every public attribute schema, across roots."""
        return {
            uid: attribute
            for root in self._roots.values()
            for uid, attribute in root.attributes.items()
        }

    @cached_property
    def _private_attributes(self) -> dict[UUID, AttributeSchema]:
        """Every private attribute schema, across roots."""
        return {
            uid: attribute
            for root in self._roots.values()
            for uid, attribute in root.private_attributes.items()
        }

    def _validate(self) -> None:
        """Refuse what the plugin provides that cannot be used, every check
        in one place.

        Raises
        ------
        ValueError
            If a root is provided twice or defines one item schema uid twice,
            an attribute schema uid has two definitions, a project in the
            database is on a root that is not provided, the projects on a
            root hold items or attributes on schemas the root does not have, or
            a migration is between roots that are not provided or not of one
            family, is not to the root of new projects, or migrates from a root
            another migration does.
        """
        self._validate_roots()
        self._validate_attributes()
        self._validate_projects()
        self._validate_stored_schemas()
        self._validate_migrations()

    def _validate_stored_schemas(self) -> None:
        """Refuse to start with projects holding items or attributes on schemas
        their root does not have.

        A project stays on the root it was created with, which is found by its
        uid alone. A root changed under the same uid, rather than given a new
        one, leaves what is stored on the schemas it no longer has.
        """
        drift: dict[UUID, tuple[int, int]] = {}
        with self._database_service.get_session() as session:
            counts = self._database_service.count_schema_uids_by_root(session)
        for root_uid, is_item, schema_uid, count in counts:
            root = self.get_root(root_uid)
            items, attributes = drift.get(root_uid, (0, 0))
            if is_item and schema_uid not in root.items:
                drift[root_uid] = (items + count, attributes)
            elif not is_item and not root.has_attribute(schema_uid):
                drift[root_uid] = (items, attributes + count)
        if drift:
            listed = ", ".join(
                f"{self.get_root(root_uid).display_name} ({root_uid}): {items} "
                f"items and {attributes} attributes"
                for root_uid, (items, attributes) in drift.items()
            )
            raise ValueError(
                f"Projects in the database hold items or attributes on schemas "
                f"their root schema does not have: {listed}. Give the changed "
                f"root a new uid, provide the old one as a previous root, and add "
                f"a migration to convert its projects."
            )

    def _validate_projects(self) -> None:
        """Refuse to start with projects on a root that is not provided:
        there would be no schema to read them with."""
        with self._database_service.get_session() as session:
            counts = session.execute(
                select(DatabaseProject.root_schema_uid, func.count()).group_by(
                    DatabaseProject.root_schema_uid
                )
            ).all()
        missing = {
            root_schema_uid: count
            for root_schema_uid, count in counts
            if root_schema_uid not in self._roots
        }
        if missing:
            listed = ", ".join(
                f"{root_schema_uid} ({count} projects)"
                for root_schema_uid, count in missing.items()
            )
            raise ValueError(
                f"Projects in the database are on root schemas that are not "
                f"provided: {listed}. Provide each as a previous root, or convert "
                f"or delete those projects first."
            )

    def _validate_roots(self) -> None:
        """Refuse a root provided twice, which a project could not tell apart,
        and a root where one item schema uid has two definitions."""
        seen: set[UUID] = set()
        for root in self._provided:
            if root.uid in seen:
                raise ValueError(f"Root schema {root.uid} is provided more than once.")
            seen.add(root.uid)
            root.validate()

    def _validate_migrations(self) -> None:
        """Refuse a migration that cannot be run, so that it is found at
        startup. Migrations are to the root of new projects only, so none is
        from it and none follows another."""
        sources = Counter(
            migration.source_root_uid for migration in self._migration_list
        )
        logger = logging.getLogger(__name__)
        for migration in self._migration_list:
            source_uid, target_uid = (
                migration.source_root_uid,
                migration.target_root_uid,
            )
            for uid in (source_uid, target_uid):
                if uid not in self._roots:
                    raise ValueError(
                        f"The migration from root schema {source_uid} to "
                        f"{target_uid} is between roots of which {uid} is not "
                        f"provided."
                    )
            source, target = self._roots[source_uid], self._roots[target_uid]
            if source_uid == target_uid or source.family_uid != target.family_uid:
                raise ValueError(
                    f"The migration from {source.display_name} to "
                    f"{target.display_name} is not between two roots of one family."
                )
            if not target.is_default:
                raise ValueError(
                    f"The migration from {source.display_name} to "
                    f"{target.display_name} is not to the root of new projects."
                )
            if sources[source_uid] > 1:
                raise ValueError(
                    f"There is more than one migration from {source.display_name}."
                )
            logger.info(
                f"Loaded the migration from {source.display_name} to "
                f"{target.display_name}."
            )

    def _validate_attributes(self) -> None:
        """Refuse schemas where one UID resolves to two different attribute
        definitions, in a root or across roots, as mappers select by it. A UID
        appearing more than once is tolerated when the schemas are field-equal
        — frozen Pydantic models compare by value, so the same attribute
        exposed in both public and private collections, or in two roots, is
        unambiguous. Item schema UIDs are only checked within a root."""
        seen: dict[UUID, AttributeSchema] = {}
        for root in self._roots.values():
            for attribute in chain(
                root.attributes.values(), root.private_attributes.values()
            ):
                existing = seen.get(attribute.uid)
                if existing is not None and existing != attribute:
                    raise ValueError(
                        f"Conflicting attribute schemas with UID {attribute.uid}: "
                        f"{existing} vs {attribute}"
                    )
                seen[attribute.uid] = attribute
