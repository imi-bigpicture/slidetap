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

from enum import Enum
from typing import Dict, Optional, Sequence, Union
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
    VALID = "valid"
    STATUS = "status"
    MESSAGE = "message"
    ATTRIBUTE = "attribute"
    RELATION = "relation"


class ColumnSort(FrozenBaseModel):
    descending: bool
    sort_type: SortType


class AttributeSort(ColumnSort):
    column: str
    sort_type: SortType = SortType.ATTRIBUTE


class RelationSort(ColumnSort):
    relation_schema_uid: UUID
    relation_type: RelationFilterType
    sort_type: SortType = SortType.RELATION


class RelationFilter(FrozenBaseModel):
    relation_schema_uid: UUID
    relation_type: RelationFilterType
    min_count: Optional[int] = None
    max_count: Optional[int] = None


class TableRequest(FrozenBaseModel):
    start: Optional[int] = None
    size: Optional[int] = None
    identifier_filter: Optional[str] = None
    attribute_filters: Optional[Dict[str, str]] = None
    relation_filters: Optional[Sequence[RelationFilter]] = None
    sorting: Optional[Sequence[Union[ColumnSort, AttributeSort, RelationSort]]] = None
    included: Optional[bool] = None
    valid: Optional[bool] = None
    status_filter: Optional[Sequence[ImageStatus]] = None
    tag_filter: Optional[Sequence[UUID]] = None
