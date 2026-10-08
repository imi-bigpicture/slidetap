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

"""The attribute migrators of a migration, by source attribute schema."""

from uuid import UUID

from slidetap.external_interfaces.implementations.migration.attribute_migrator import (
    AttributeMigrator,
)
from slidetap.model import AttributeSchema


class AttributeMigrators:
    """The attribute migrator and target attribute schema of each source
    attribute schema whose attributes change, registered one by one.

    A migration looks up an attribute here to migrate the attribute of a
    mapping item, and the target of an attribute schema to move a mapper to.
    """

    def __init__(self):
        """Create the registry, empty."""
        self._migrators: dict[UUID, tuple[AttributeMigrator, AttributeSchema]] = {}

    def register(
        self,
        source: AttributeSchema,
        migrator: AttributeMigrator,
        target: AttributeSchema,
    ) -> None:
        """Register how the attributes of a source attribute schema migrate.

        Parameters
        ----------
        source: AttributeSchema
            The attribute schema of the source root.
        migrator: AttributeMigrator
            The migrator of its attributes.
        target: AttributeSchema
            The attribute schema of the target root they migrate to.

        Raises
        ------
        ValueError
            If the source attribute schema is registered already.
        """
        if source.uid in self._migrators:
            raise ValueError(
                f"Attribute schema {source.tag} ({source.uid}) is registered already."
            )
        self._migrators[source.uid] = (migrator, target)

    def get(self, schema_uid: UUID) -> tuple[AttributeMigrator, AttributeSchema] | None:
        """Get the migrator and target of a source attribute schema.

        Parameters
        ----------
        schema_uid: UUID
            The uid of the source attribute schema.

        Returns
        -------
        tuple[AttributeMigrator, AttributeSchema] | None
            The migrator and the target attribute schema, or None where the
            schema is not registered.
        """
        return self._migrators.get(schema_uid)

    def __contains__(self, schema_uid: object) -> bool:
        """Check if a source attribute schema uid is registered."""
        return schema_uid in self._migrators
