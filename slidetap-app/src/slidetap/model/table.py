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

from collections.abc import Sequence
from enum import Enum
from uuid import UUID

from slidetap.model.base_model import FrozenBaseModel
from slidetap.model.image_status import ImageStatus


class RelationFilterType(Enum):
    PARENT = "parent"
    CHILD = "child"
    IMAGE = "image"
    OBSERVATION = "observation"
    ANNOTATION = "annotation"
    SAMPLE = "sample"


class SortType(Enum):
    IDENTIFIER = "identifier"
    PSEUDONYM = "pseudonym"
    VALID = "valid"
    STATUS = "status"
    MESSAGE = "message"
    ATTRIBUTE = "attribute"
    RELATION = "relation"


class AttributeValueField(Enum):
    """Value of an attribute to filter and sort an attribute column on."""

    DISPLAY = "display"
    MAPPABLE = "mappable"


class ColumnSort(FrozenBaseModel):
    descending: bool
    sort_type: SortType


class AttributeSort(ColumnSort):
    column: str
    field: AttributeValueField = AttributeValueField.DISPLAY
    sort_type: SortType = SortType.ATTRIBUTE


class AttributeFilter(FrozenBaseModel):
    """One term a column was filtered by.

    A column can be filtered by several terms at once, which is why this is a
    term rather than the whole filter: the terms of one column are read
    together, and what they mean together is up to whoever runs the query.
    """

    tag: str
    value: str
    field: AttributeValueField = AttributeValueField.DISPLAY
    negated: bool = False
    """Wanted for not matching, rather than for matching.

    An item that has no attribute of this tag at all counts as not matching:
    a case with no diagnosis is not a case diagnosed with what is excluded.
    """


class RelationSort(ColumnSort):
    relation_schema_uid: UUID
    relation_type: RelationFilterType
    sort_type: SortType = SortType.RELATION


class RelationFilter(FrozenBaseModel):
    relation_schema_uid: UUID
    relation_type: RelationFilterType
    min_count: int | None = None
    max_count: int | None = None


class TableRequest(FrozenBaseModel):
    start: int | None = None
    size: int | None = None
    identifier_filter: str | None = None
    pseudonym_mode: bool = False
    attribute_filters: Sequence[AttributeFilter] | None = None
    relation_filters: Sequence[RelationFilter] | None = None
    sorting: Sequence[ColumnSort | AttributeSort | RelationSort] | None = None
    included: bool | None = None
    valid: bool | None = None
    status_filter: Sequence[ImageStatus] | None = None
    tag_filter: Sequence[UUID] | None = None
