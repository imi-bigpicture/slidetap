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

"""Helpers for implementing schema migrations."""

from slidetap.external_interfaces.implementations.migration.attribute_migrator import (
    AttributeMigrator,
    EnumAttributeMigrator,
    FixedValueAttributeMigrator,
    MigratedAttribute,
)
from slidetap.external_interfaces.implementations.migration.attribute_migrators import (
    AttributeMigrators,
    UnchangedAttributeMigrator,
)
from slidetap.external_interfaces.implementations.migration.entity_migrator import (
    EntityMigrator,
)
from slidetap.external_interfaces.implementations.migration.root_schema_migration import (  # noqa: E501
    RootSchemaMigration,
)

__all__ = [
    "AttributeMigrator",
    "AttributeMigrators",
    "EntityMigrator",
    "EnumAttributeMigrator",
    "FixedValueAttributeMigrator",
    "MigratedAttribute",
    "RootSchemaMigration",
    "UnchangedAttributeMigrator",
]
