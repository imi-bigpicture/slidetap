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

"""What migrating a project to another root schema does to it."""

from uuid import UUID

from pydantic import Field

from slidetap.model.base_model import CamelCaseBaseModel


class MigrationAttributeChange(CamelCaseBaseModel):
    """What migrating does to the attributes of one attribute schema.

    Counted by attribute: an object holds an attribute of a schema once.
    """

    attribute_schema_uid: UUID
    """The schema of the attributes: of the source root for what is dropped,
    of the target root for what is invalid."""

    tag: str
    display_name: str

    dropped: int = 0
    """Attributes with a value that the migration left out."""

    invalid: int = 0
    """Attributes that are not valid after the migration, a required one that
    has no value included."""


class MigrationReport(CamelCaseBaseModel):
    """What migrating a project does, found by migrating it and validating the
    result: in a transaction that is rolled back for a dry run."""

    project_uid: UUID
    source_root_schema_uid: UUID
    target_root_schema_uid: UUID
    target_root_schema_name: str
    """The name and version of the target root."""

    items: int
    """How many items are migrated, the project and the dataset not counted."""

    attributes: list[MigrationAttributeChange] = Field(default_factory=list)
    """The attribute schemas with attributes dropped or invalid, and how many."""
