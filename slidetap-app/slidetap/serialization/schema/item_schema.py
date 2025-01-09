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

from abc import abstractmethod
from typing import Any, Dict, Type

from marshmallow import fields, post_load
from slidetap.model.item_value_type import ItemValueType
from slidetap.model.schema.item_relation import ItemRelation
from slidetap.model.schema.item_schema import (
    AnnotationSchema,
    AnnotationToImageRelation,
    ImageSchema,
    ImageToSampleRelation,
    ItemSchema,
    ObservationSchema,
    ObservationToAnnotationRelation,
    ObservationToImageRelation,
    ObservationToSampleRelation,
    SampleSchema,
    SampleToSampleRelation,
)
from slidetap.serialization.base import BaseModel
from slidetap.serialization.schema.attribute_schema import AttributeSchemaDictField


class ItemSchemaBaseModel(BaseModel):
    """Base without children and parents to avoid circular dependencies."""

    uid = fields.UUID(required=True)
    name = fields.String(required=True)
    display_name = fields.String(required=True)
    item_value_type = fields.Enum(
        ItemValueType,
        by_value=True,
    )
    attributes = AttributeSchemaDictField()

    @property
    @abstractmethod
    def _load_type(self) -> Type[ItemSchema]:
        raise NotImplementedError()

    @post_load
    def post_load(self, data: Dict[str, Any], **kwargs) -> ItemSchema:
        return self._load_type(**data)


class ItemRelationModel(BaseModel):
    uid = fields.UUID()
    name = fields.String()
    description = fields.String(allow_none=True)

    @property
    @abstractmethod
    def _load_type(self) -> Type[ItemRelation]:
        raise NotImplementedError()

    @post_load
    def post_load(self, data: Dict[str, Any], **kwargs):
        return self._load_type(**data)


class SampleToSampleRelationModel(ItemRelationModel):
    parent_title = fields.String()
    child_title = fields.String()
    parent_uid = fields.UUID()
    child_uid = fields.UUID()
    min_parents = fields.Integer(allow_none=True)
    max_parents = fields.Integer(allow_none=True)
    min_children = fields.Integer(allow_none=True)
    max_children = fields.Integer(allow_none=True)

    @property
    def _load_type(self) -> Type[SampleToSampleRelation]:
        return SampleToSampleRelation


class ImageToSampleRelationModel(ItemRelationModel):
    image_title = fields.String()
    sample_title = fields.String()
    image_uid = fields.UUID()
    sample_uid = fields.UUID()

    @property
    def _load_type(self) -> Type[ItemRelation]:
        return ImageToSampleRelation


class AnnotationToImageRelationModel(ItemRelationModel):
    annotation_title = fields.String()
    image_title = fields.String()
    annotation_uid = fields.UUID()
    image_uid = fields.UUID()

    @property
    def _load_type(self) -> Type[ItemRelation]:
        return AnnotationToImageRelation


class ObservationToSampleRelationModel(ItemRelationModel):
    observation_title = fields.String()
    sample_title = fields.String()
    observation_uid = fields.UUID()
    sample_uid = fields.UUID()

    @property
    def _load_type(self) -> Type[ItemRelation]:
        return ObservationToSampleRelation


class ObservationToImageRelationModel(ItemRelationModel):
    observation_title = fields.String()
    image_title = fields.String()
    observation_uid = fields.UUID()
    image_uid = fields.UUID()

    @property
    def _load_type(self) -> Type[ItemRelation]:
        return ObservationToImageRelation


class ObservationToAnnotationRelationModel(ItemRelationModel):
    observation_title = fields.String()
    annotation_title = fields.String()
    observation_uid = fields.UUID()
    annotation_uid = fields.UUID()

    @property
    def _load_type(self) -> Type[ItemRelation]:
        return ObservationToAnnotationRelation


class SampleSchemaModel(ItemSchemaBaseModel):
    children = fields.List(fields.Nested(SampleToSampleRelationModel))
    parents = fields.List(fields.Nested(SampleToSampleRelationModel))
    images = fields.List(fields.Nested(ImageToSampleRelationModel))
    observations = fields.List(fields.Nested(ObservationToSampleRelationModel))
    item_value_type = fields.Constant(ItemValueType.SAMPLE.value)

    @property
    def _load_type(self) -> Type[SampleSchema]:
        return SampleSchema


class ImageSchemaModel(ItemSchemaBaseModel):
    samples = fields.List(fields.Nested(ImageToSampleRelationModel))
    annotations = fields.List(fields.Nested(AnnotationToImageRelationModel))
    observations = fields.List(fields.Nested(ObservationToImageRelationModel))
    item_value_type = fields.Constant(ItemValueType.IMAGE.value)

    @property
    def _load_type(self) -> Type[ImageSchema]:
        return ImageSchema


class AnnotationSchemaModel(ItemSchemaBaseModel):
    images = fields.List(fields.Nested(AnnotationToImageRelationModel))
    observations = fields.List(fields.Nested(ObservationToAnnotationRelationModel))
    item_value_type = fields.Constant(ItemValueType.ANNOTATION.value)

    @property
    def _load_type(self) -> Type[AnnotationSchema]:
        return AnnotationSchema


class ObservationSchemaModel(ItemSchemaBaseModel):
    samples = fields.List(fields.Nested(ObservationToSampleRelationModel))
    images = fields.List(fields.Nested(ObservationToImageRelationModel))
    annotations = fields.List(fields.Nested(ObservationToAnnotationRelationModel))
    item_value_type = fields.Constant(ItemValueType.OBSERVATION.value)

    @property
    def _load_type(self) -> Type[ObservationSchema]:
        return ObservationSchema


class ItemSchemaModel(BaseModel):
    def dump(self, item_schema: ItemSchema, **kwargs):
        if isinstance(item_schema, SampleSchema):
            return SampleSchemaModel().dump(item_schema, **kwargs)
        if isinstance(item_schema, ImageSchema):
            return ImageSchemaModel().dump(item_schema, **kwargs)
        if isinstance(item_schema, AnnotationSchema):
            return AnnotationSchemaModel().dump(item_schema, **kwargs)
        if isinstance(item_schema, ObservationSchema):
            return ObservationSchemaModel().dump(item_schema, **kwargs)
        raise ValueError(f"Unknown schema {item_schema}.")

    def load(self, data: Dict[str, Any], **kwargs) -> ItemSchema:
        item_value_type = ItemValueType(data["itemValueType"])
        if item_value_type == ItemValueType.SAMPLE:
            return SampleSchemaModel().load(data, **kwargs)  # type: ignore
        if item_value_type == ItemValueType.IMAGE:
            return ImageSchemaModel().load(data, **kwargs)  # type: ignore
        if item_value_type == ItemValueType.ANNOTATION:
            return AnnotationSchemaModel().load(data, **kwargs)  # type: ignore
        if item_value_type == ItemValueType.OBSERVATION:
            return ObservationSchemaModel().load(data, **kwargs)  # type: ignore
        raise ValueError(f"Unknown schema {item_value_type}.")
