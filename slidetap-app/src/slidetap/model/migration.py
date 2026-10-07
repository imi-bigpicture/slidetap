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

"""The migration of a project to another root schema, in steps."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import Field

from slidetap.model.attribute import AnyAttribute
from slidetap.model.base_model import CamelCaseBaseModel
from slidetap.model.project_status import ProjectStatus


class MigrationState(Enum):
    """Where the migration of a project is."""

    PLANNING = "planning"
    """The migration is run, without saving, to find what the curator
    decides."""

    CURATING = "curating"
    """The curator decides the issues, and submits or aborts."""

    COMPLETING = "completing"
    """The migration is run again, with the decisions, and saved."""

    FAILED = "failed"
    """Planning or completing failed, with nothing of the project changed. It
    can only be aborted."""


class MigrationObjectKind(Enum):
    """What kind of object of a project an issue is about."""

    PROJECT = "project"
    DATASET = "dataset"
    ITEM = "item"


class MigrationIssue(CamelCaseBaseModel):
    """A top-level attribute of the target schema of an object that the
    migration could not convert, and what the curator decided."""

    uid: UUID
    tag: str
    """The tag in the target schema."""

    attribute_schema_uid: UUID
    """The attribute schema of the tag in the target root, which a decided
    value is on."""

    display_name: str
    """The display name of the target attribute."""

    original: AnyAttribute
    """The attribute of the source object."""

    proposed: AnyAttribute | None = None
    """What could be converted, for the curator to start from."""

    reason: str
    """Why the attribute was not converted."""

    decided: bool = False
    left_empty: bool = False
    """Whether the attribute was decided to be left empty."""

    decision: AnyAttribute | None = None
    """The decided value, None where it is left empty or not decided."""


class MigrationDecision(CamelCaseBaseModel):
    """The curator's decision of an issue."""

    attribute: AnyAttribute | None = None
    """The value, on the attribute schema of the issue, or None to leave the
    attribute empty."""


class MigrationDroppedAttribute(CamelCaseBaseModel):
    """An attribute with a value that the migration left out, as it has no
    target. Nothing is decided of it."""

    tag: str
    """The tag in the source schema."""

    display_name: str
    display_value: str | None = None


class MigrationObject(CamelCaseBaseModel):
    """A project, dataset, or item with issues to decide or attributes
    dropped."""

    uid: UUID
    kind: MigrationObjectKind
    identifier: str
    """The name of the project or dataset, the identifier of an item."""

    schema_uid: UUID
    """The schema of the target root it is migrated to."""

    schema_display_name: str
    issues: list[MigrationIssue] = Field(default_factory=list)
    dropped: list[MigrationDroppedAttribute] = Field(default_factory=list)


class ProjectMigration(CamelCaseBaseModel):
    """The migration of a project, with its plan once planned."""

    project_uid: UUID
    source_root_schema_uid: UUID
    target_root_schema_uid: UUID
    target_root_schema_name: str
    """The name and version of the target root."""

    previous_status: ProjectStatus
    """The status the project had, which it gets back when the migration is
    completed or aborted."""

    state: MigrationState
    error: str | None = None
    """Why planning or completing failed."""

    created: datetime
    updated: datetime
    objects: list[MigrationObject] = Field(default_factory=list)
    """The objects with issues or dropped attributes: the project, the
    dataset, then the items by identifier."""

    issues: int = 0
    """How many issues there are."""

    decided: int = 0
    """How many issues are decided."""
