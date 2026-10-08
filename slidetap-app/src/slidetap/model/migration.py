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

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import Field

from slidetap.model.attribute import AnyAttribute
from slidetap.model.base_model import CamelCaseBaseModel
from slidetap.model.project_status import ProjectStatus


@dataclass(frozen=True)
class UnresolvedAttribute:
    """An attribute a migration could not convert by itself, for the curator
    to decide."""

    original: AnyAttribute | None
    """The attribute of the source object, or None where it had none."""

    proposed: AnyAttribute | None
    """What could be converted, on the attribute schema of the target tag, for
    the curator to start from, or None."""

    reason: str
    """Why the attribute was not converted."""


@dataclass(frozen=True)
class MigratedObject:
    """What a migration may change of a project, dataset, or item: the schema
    it is on, and its attributes.

    Everything else, such as the uid, the relations, the images, the review
    status, and the pseudonym, is kept by core as it is.
    """

    schema_uid: UUID
    """The project, dataset, or item schema of the target root, of the same
    kind as the one it was on."""

    attributes: Mapping[str, AnyAttribute] = field(default_factory=dict)
    """The attributes by tag, each on the attribute schema of that tag in the
    target schema. An attribute left out is dropped."""

    private_attributes: Mapping[str, AnyAttribute] = field(default_factory=dict)
    """The private attributes, as `attributes`."""

    unresolved: Mapping[str, UnresolvedAttribute] = field(default_factory=dict)
    """What the curator resolves, by tag of the target schema, a public or else
    a private attribute, which is in neither `attributes` nor
    `private_attributes`. The resolved value is put at the tag, or nothing."""


class MigrationStatus(Enum):
    """Where the migration of a project is."""

    PLANNING = "planning"
    """The migration is run, without saving, to find what the curator
    decides."""

    CURATING = "curating"
    """The curator resolves the attribute issues, accepts the dropped
    attributes, and submits or reverts."""

    COMPLETING = "completing"
    """The migration is run again, with the resolved values, and saved."""

    FAILED = "failed"
    """Planning or completing failed, with nothing of the project changed. It
    can only be reverted."""


class MigrationObjectKind(Enum):
    """What kind of object of a project a migration object is."""

    PROJECT = "project"
    """The project."""

    DATASET = "dataset"
    """The dataset of the project."""

    ITEM = "item"
    """An item of the dataset."""


class MigrationAttributeIssue(CamelCaseBaseModel):
    """A top-level attribute of an object that the migration could not
    convert, left invalid, or dropped, and how the curator resolved it."""

    uid: UUID
    tag: str
    """The tag in the target schema, or in the source schema for a dropped
    attribute."""

    source_attribute_schema_uid: UUID | None = None
    """The attribute schema of the original in the source root, None where the
    object had no attribute."""

    target_attribute_schema_uid: UUID | None = None
    """The attribute schema of the tag in the target root, which a resolved
    value is on, None for a dropped attribute."""

    dropped: bool = False
    """Whether the migration dropped the attribute, which the curator can only
    accept."""

    display_name: str
    """The display name of the target attribute, or of the source attribute
    for a dropped attribute."""

    original: AnyAttribute | None = None
    """The attribute of the source object, None where it had none."""

    proposed: AnyAttribute | None = None
    """What could be converted, for the curator to start from."""

    problem: str
    """What needs the curator's decision: a value the migration could not
    migrate, an attribute the migration made invalid, or an attribute it
    dropped."""

    resolved_at: datetime | None = None
    """When the issue was resolved, or the dropped attribute accepted, None
    until it is."""

    left_empty: bool = False
    """Whether the attribute issue was resolved by leaving it empty."""

    resolved: AnyAttribute | None = None
    """The value the issue is resolved with, None where left empty, accepted
    as dropped, or not yet resolved."""


class MigrationResolution(CamelCaseBaseModel):
    """How the curator resolves an attribute issue."""

    attribute: AnyAttribute | None = None
    """The value, on the attribute schema of the attribute issue, or None to
    leave the attribute empty or accept a dropped attribute."""


class MigrationObject(CamelCaseBaseModel):
    """A project, dataset, or item with attribute issues to resolve."""

    uid: UUID
    kind: MigrationObjectKind
    """Whether it is the project, the dataset, or an item."""

    identifier: str
    """The name of the project or dataset, the identifier of an item."""

    target_schema_uid: UUID
    """The schema of the target root it is migrated to."""

    target_schema_display_name: str
    """The display name of the target schema."""

    attribute_issues: list[MigrationAttributeIssue] = Field(default_factory=list)
    """The attribute issues of the object, the dropped attributes included."""


class ProjectMigration(CamelCaseBaseModel):
    """The migration of a project, with its plan once planned."""

    project_uid: UUID
    source_root_schema_uid: UUID
    """The root the project is on."""

    target_root_schema_uid: UUID
    """The root the project is migrated to."""

    target_root_schema_name: str
    """The name and version of the target root."""

    previous_project_status: ProjectStatus
    """The status the project had, which it gets back when the migration is
    completed or reverted."""

    status: MigrationStatus
    """Where the migration is."""

    error: str | None = None
    """Why planning or completing failed."""

    created: datetime
    updated: datetime
    objects: list[MigrationObject] = Field(default_factory=list)
    """The objects with attribute issues: the project, the dataset, then the
    items by identifier."""

    attribute_issues: int = 0
    """How many attribute issues there are, the dropped attributes included."""

    resolved: int = 0
    """How many attribute issues are resolved or accepted."""
