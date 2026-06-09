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

from typing import Literal
from uuid import UUID

from pydantic import Field

from slidetap.model.base_model import FrozenBaseModel
from slidetap.model.item_value_type import ItemValueType
from slidetap.model.schema.attribute_schema import (
    AnyAttributeSchema,
    AttributeGroupLayout,
)
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
    attributes: dict[str, AnyAttributeSchema] = Field(default_factory=dict)
    private_attributes: dict[str, AnyAttributeSchema] = Field(default_factory=dict)
    attribute_layout: list[AttributeGroupLayout] = Field(default_factory=list)
    private_attribute_layout: list[AttributeGroupLayout] = Field(default_factory=list)
    pseudonym_required: bool = False


class ObservationSchema(ItemSchema):
    """Schema for observation items."""

    samples: tuple[ObservationToSampleRelation, ...] = Field(default_factory=tuple)
    images: tuple[ObservationToImageRelation, ...] = Field(default_factory=tuple)
    annotations: tuple[ObservationToAnnotationRelation, ...] = Field(
        default_factory=tuple
    )
    item_value_type: Literal[ItemValueType.OBSERVATION] = ItemValueType.OBSERVATION


class AnnotationSchema(ItemSchema):
    """Schema for annotation items."""

    images: tuple[AnnotationToImageRelation, ...] = Field(default_factory=tuple)
    observations: tuple[ObservationToAnnotationRelation, ...] = Field(
        default_factory=tuple
    )
    item_value_type: Literal[ItemValueType.ANNOTATION] = ItemValueType.ANNOTATION


class ImageSchema(ItemSchema):
    """Schema for image items."""

    samples: tuple[ImageToSampleRelation, ...] = Field(default_factory=tuple)
    observations: tuple[ObservationToImageRelation, ...] = Field(default_factory=tuple)
    annotations: tuple[AnnotationToImageRelation, ...] = Field(default_factory=tuple)
    item_value_type: Literal[ItemValueType.IMAGE] = ItemValueType.IMAGE


class SampleSchema(ItemSchema):
    """Schema for sample items."""

    children: tuple[SampleToSampleRelation, ...] = Field(default_factory=tuple)
    parents: tuple[SampleToSampleRelation, ...] = Field(default_factory=tuple)
    images: tuple[ImageToSampleRelation, ...] = Field(default_factory=tuple)
    observations: tuple[ObservationToSampleRelation, ...] = Field(default_factory=tuple)
    item_value_type: Literal[ItemValueType.SAMPLE] = ItemValueType.SAMPLE
