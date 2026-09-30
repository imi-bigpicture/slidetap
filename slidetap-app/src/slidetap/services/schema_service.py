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

from collections.abc import Mapping
from functools import cached_property
from itertools import chain
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import object_session

from slidetap.database import (
    DatabaseDataset,
    DatabaseItem,
    DatabaseProject,
)
from slidetap.external_interfaces.schema import SchemaInterface
from slidetap.model import (
    AttributeSchema,
    NotFoundError,
    Project,
    RootSchemaIndex,
)
from slidetap.services.database_service import DatabaseService


class SchemaService:
    """Schema service should be used to interface with schemas.

    Holds every root schema the application provides. Which of them a project
    uses is stated by the project, and every operation on the project looks up
    its item schemas within that root. Attribute schemas are looked up across
    roots, as an attribute schema uid means one definition wherever it is used.
    """

    def __init__(
        self,
        schema_interface: SchemaInterface,
        database_service: DatabaseService,
    ):
        """Create a schema service, asking the plugin for its roots once.

        Parameters
        ----------
        schema_interface: SchemaInterface
            The plugin's schema interface: its `root()` is the root of new
            projects, and its `previous_roots()` the roots of earlier versions.
        database_service: DatabaseService
            Where the projects are, which have to be on a provided root.

        Raises
        ------
        ValueError
            If the roots cannot be used, see `_validate()`.
        """
        self._database_service = database_service
        self._default_root = RootSchemaIndex(schema_interface.root())
        self._provided = [
            self._default_root,
            *(RootSchemaIndex(schema) for schema in schema_interface.previous_roots()),
        ]
        self._roots: dict[UUID, RootSchemaIndex] = {
            root.uid: root for root in self._provided
        }
        self._validate()

    @property
    def default_root(self) -> RootSchemaIndex:
        """The root of new projects."""
        return self._default_root

    @property
    def roots(self) -> Mapping[UUID, RootSchemaIndex]:
        """Every root the application provides, by uid."""
        return self._roots

    def has_root(self, root_schema_uid: UUID) -> bool:
        return root_schema_uid in self._roots

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
        subject: Project | DatabaseProject | DatabaseDataset | DatabaseItem | None,
    ) -> RootSchemaIndex:
        """The root of the project something belongs to. Nothing, or a dataset
        not yet given a project, is on the root of new projects, which is the
        one it will be given.

        An item just added has its dataset uid but not yet its dataset, which
        is then read from the session the item is in. The dataset is normally
        there already, so that this does not query in the middle of an import.
        """
        if subject is None:
            return self._default_root
        if isinstance(subject, (Project, DatabaseProject)):
            return self.get_root(subject.root_schema_uid)
        if isinstance(subject, DatabaseDataset):
            return self.root_of(subject.project)
        dataset = subject.dataset
        if dataset is None:
            session = object_session(subject)
            if session is not None:
                dataset = session.get(DatabaseDataset, subject.dataset_uid)
        return self.root_of(dataset)

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
            an attribute schema uid has two definitions, or a project in the
            database is on a root that is not provided.
        """
        self._validate_roots()
        self._validate_attributes()
        self._validate_projects()

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
