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

"""Item schema models for defining different types of items."""

from typing import Dict, Literal, Tuple
from uuid import UUID

from pydantic import Field
from slidetap.model.base_model import FrozenBaseModel
from slidetap.model.item_value_type import ItemValueType
from slidetap.model.schema.attribute_schema import AnyAttributeSchema
from slidetap.model.schema.item_relation import (
    AnnotationToImageRelation,
    ImageToSampleRelation,
    ObservationToAnnotationRelation,
    ObservationToImageRelation,
    ObservationToSampleRelation,
    SampleToSampleRelation,
)


class ItemSchema(FrozenBaseModel):
    """Base schema for all item types."""

    uid: UUID
    name: str
    display_name: str
    display_order: int
    attributes: Dict[str, AnyAttributeSchema] = Field(default_factory=dict)
    private_attributes: Dict[str, AnyAttributeSchema] = Field(default_factory=dict)
    item_value_type: ItemValueType


class ObservationSchema(ItemSchema):
    """Schema for observation items."""

    samples: Tuple[ObservationToSampleRelation, ...] = Field(default_factory=tuple)
    images: Tuple[ObservationToImageRelation, ...] = Field(default_factory=tuple)
    annotations: Tuple[ObservationToAnnotationRelation, ...] = Field(
        default_factory=tuple
    )
    item_value_type: Literal[ItemValueType.OBSERVATION] = ItemValueType.OBSERVATION


class AnnotationSchema(ItemSchema):
    """Schema for annotation items."""

    images: Tuple[AnnotationToImageRelation, ...] = Field(default_factory=tuple)
    observations: Tuple[ObservationToAnnotationRelation, ...] = Field(
        default_factory=tuple
    )
    item_value_type: Literal[ItemValueType.ANNOTATION] = ItemValueType.ANNOTATION


class ImageSchema(ItemSchema):
    """Schema for image items."""

    samples: Tuple[ImageToSampleRelation, ...] = Field(default_factory=tuple)
    observations: Tuple[ObservationToImageRelation, ...] = Field(default_factory=tuple)
    annotations: Tuple[AnnotationToImageRelation, ...] = Field(default_factory=tuple)
    item_value_type: Literal[ItemValueType.IMAGE] = ItemValueType.IMAGE


class SampleSchema(ItemSchema):
    """Schema for sample items."""

    children: Tuple[SampleToSampleRelation, ...] = Field(default_factory=tuple)
    parents: Tuple[SampleToSampleRelation, ...] = Field(default_factory=tuple)
    images: Tuple[ImageToSampleRelation, ...] = Field(default_factory=tuple)
    observations: Tuple[ObservationToSampleRelation, ...] = Field(default_factory=tuple)
    item_value_type: Literal[ItemValueType.SAMPLE] = ItemValueType.SAMPLE
