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

from typing import Any, Dict, Iterable, Optional
from uuid import UUID

from marshmallow import fields, post_load, pre_load
from slidetap.database import (
    AnnotationSchema,
    AttributeSchema,
    BooleanAttributeSchema,
    CodeAttributeSchema,
    DatetimeAttributeSchema,
    EnumAttributeSchema,
    ImageSchema,
    ItemSchema,
    ItemValueType,
    ListAttributeSchema,
    MeasurementAttributeSchema,
    NumericAttributeSchema,
    ObjectAttributeSchema,
    ObservationSchema,
    ProjectSchema,
    SampleSchema,
    StringAttributeSchema,
    UnionAttributeSchema,
)
from slidetap.web.model import AttributeValueType, DatetimeType
from slidetap.web.serialization.base import BaseModel


class AttributeSchemaOneOfModel(BaseModel):
    def dump(self, attribute_schema: AttributeSchema, **kwargs):
        if isinstance(attribute_schema, StringAttributeSchema):
            return StringAttributeSchemaModel().dump(attribute_schema, **kwargs)
        if isinstance(attribute_schema, DatetimeAttributeSchema):
            return DatetimeAttributeSchemaModel().dump(attribute_schema, **kwargs)
        if isinstance(attribute_schema, NumericAttributeSchema):
            return NumericAttributeSchemaModel().dump(attribute_schema, **kwargs)
        if isinstance(attribute_schema, MeasurementAttributeSchema):
            return MeasurementAttributeSchemaModel().dump(attribute_schema, **kwargs)
        if isinstance(attribute_schema, CodeAttributeSchema):
            return CodeAttributeSchemaModel().dump(attribute_schema, **kwargs)
        if isinstance(attribute_schema, BooleanAttributeSchema):
            return BooleanAttributeSchemaModel().dump(attribute_schema, **kwargs)
        if isinstance(attribute_schema, ObjectAttributeSchema):
            return ObjectAttributeSchemaModel().dump(attribute_schema, **kwargs)
        if isinstance(attribute_schema, ListAttributeSchema):
            return ListAttributeSchemaModel().dump(attribute_schema, **kwargs)
        if isinstance(attribute_schema, UnionAttributeSchema):
            return UnionAttributeSchemaModel().dump(attribute_schema, **kwargs)
        if isinstance(attribute_schema, EnumAttributeSchema):
            return EnumAttributeSchemaModel().dump(attribute_schema, **kwargs)
        raise ValueError(f"Unknown schema {attribute_schema}.")

    def load(self, data: Dict[str, Any], **kwargs):
        return AttributeSchemaModel().load(data, **kwargs)


class AttributeSchemaField(fields.Field):
    def _serialize(
        self, value: AttributeSchema, attr: Optional[str], obj: Any, **kwargs
    ):
        model = self._create_model(value)
        return model.dump(value)

    def _deserialize(
        self, value: Any, attr: Optional[str], data: Optional[Dict[str, Any]], **kwargs
    ):
        uid = UUID(hex=value["uid"])
        attribute_schema = AttributeSchema.get_by_uid(uid)
        return attribute_schema
        model = self._create_model_from_value_type(
            AttributeValueType(value["attributeValueType"])
        )
        return model.load(value)

    def _create_model(self, attribute_schema: AttributeSchema):
        if isinstance(attribute_schema, StringAttributeSchema):
            return StringAttributeSchemaModel()
        if isinstance(attribute_schema, DatetimeAttributeSchema):
            return DatetimeAttributeSchemaModel()
        if isinstance(attribute_schema, NumericAttributeSchema):
            return NumericAttributeSchemaModel()
        if isinstance(attribute_schema, MeasurementAttributeSchema):
            return MeasurementAttributeSchemaModel()
        if isinstance(attribute_schema, CodeAttributeSchema):
            return CodeAttributeSchemaModel()
        if isinstance(attribute_schema, BooleanAttributeSchema):
            return BooleanAttributeSchemaModel()
        if isinstance(attribute_schema, ObjectAttributeSchema):
            return ObjectAttributeSchemaModel()
        if isinstance(attribute_schema, ListAttributeSchema):
            return ListAttributeSchemaModel()
        if isinstance(attribute_schema, EnumAttributeSchema):
            return EnumAttributeSchemaModel()
        if isinstance(attribute_schema, UnionAttributeSchema):
            return UnionAttributeSchemaModel()
        raise ValueError(f"Unknown schema {attribute_schema.name}.")

    def _create_model_from_value_type(self, attribute_value_type: AttributeValueType):
        if attribute_value_type == AttributeValueType.STRING:
            return StringAttributeSchemaModel()
        if attribute_value_type == AttributeValueType.DATETIME:
            return DatetimeAttributeSchemaModel()
        if attribute_value_type == AttributeValueType.NUMERIC:
            return NumericAttributeSchemaModel()
        if attribute_value_type == AttributeValueType.MEASUREMENT:
            return MeasurementAttributeSchemaModel()
        if attribute_value_type == AttributeValueType.CODE:
            return CodeAttributeSchemaModel()
        if attribute_value_type == AttributeValueType.BOOLEAN:
            return BooleanAttributeSchemaModel()
        if attribute_value_type == AttributeValueType.OBJECT:
            return ObjectAttributeSchemaModel()
        if attribute_value_type == AttributeValueType.LIST:
            return ListAttributeSchemaModel()
        if attribute_value_type == AttributeValueType.ENUM:
            return EnumAttributeSchemaModel()
        if attribute_value_type == AttributeValueType.UNION:
            return UnionAttributeSchemaModel()
        raise ValueError(f"Unknown schema {attribute_value_type}.")


class AttributeSchemaModel(BaseModel):
    uid = fields.UUID(required=True)
    tag = fields.String()
    display_name = fields.String()
    attribute_value_type = fields.Enum(AttributeValueType, by_value=True)
    display_in_table = fields.Boolean()
    schema_uid = fields.UUID(required=True)
    optional = fields.Boolean()
    read_only = fields.Boolean()

    @post_load
    def post_load(self, data: Dict[str, Any], **kwargs):
        uid = data["uid"]
        return AttributeSchema.get_by_uid(uid)


class StringAttributeSchemaModel(AttributeSchemaModel):
    pass


class EnumAttributeSchemaModel(AttributeSchemaModel):
    allowed_values = fields.List(fields.String, allow_none=True)


class DatetimeAttributeSchemaModel(AttributeSchemaModel):
    datetime_type = fields.Enum(DatetimeType, by_value=True)


class NumericAttributeSchemaModel(AttributeSchemaModel):
    is_int = fields.Boolean()


class MeasurementAttributeSchemaModel(AttributeSchemaModel):
    allowed_units = fields.List(fields.String, allow_none=True)


class CodeAttributeSchemaModel(AttributeSchemaModel):
    allowed_schemas = fields.List(
        fields.String,
        allow_none=True,
    )


class BooleanAttributeSchemaModel(AttributeSchemaModel):
    true_display_value = fields.String()
    false_display_value = fields.String()


class ObjectAttributeSchemaModel(AttributeSchemaModel):
    display_attributes_in_parent = fields.Boolean()
    attributes = fields.List(AttributeSchemaField())


class ListAttributeSchemaModel(AttributeSchemaModel):
    display_attributes_in_parent = fields.Boolean()
    attribute = fields.Nested(AttributeSchemaOneOfModel)


class UnionAttributeSchemaModel(AttributeSchemaModel):
    attributes = fields.List(AttributeSchemaField())


class ProjectSchemaModel(BaseModel):
    uid = fields.UUID(required=True)
    name = fields.String(
        required=True,
    )
    display_name = fields.String(
        required=True,
    )
    attributes = fields.List(fields.Nested(AttributeSchemaOneOfModel), dump_only=True)
    schema_uid = fields.UUID(required=True)

    @pre_load
    def pre_load(self, data: Dict[str, Any], **kwargs):
        data.pop("attributes", None)
        return data

    @post_load
    def post_load(self, data: Dict[str, Any], **kwargs):
        uid = data["uid"]
        return ProjectSchema.get(uid)


class ItemSchemaModel(BaseModel):
    """Base without children and parents to avoid circular dependencies."""

    uid = fields.UUID(required=True)
    name = fields.String(
        required=True,
    )
    display_name = fields.String(
        required=True,
    )
    item_value_type = fields.Enum(
        ItemValueType,
        by_value=True,
    )
    attributes = fields.List(fields.Nested(AttributeSchemaOneOfModel))
    schema_uid = fields.UUID(required=True)

    @post_load
    def post_load(self, data: Dict[str, Any], **kwargs):
        uid = data["uid"]
        return ItemSchema.get_by_uid(uid)


class ItemRelation(BaseModel):
    uid = fields.UUID()
    name = fields.String()
    description = fields.String(allow_none=True)


class SampleToSampleRelationModel(ItemRelation):
    parent = fields.Nested(ItemSchemaModel)
    child = fields.Nested(ItemSchemaModel)
    min_parents = fields.Integer(allow_none=True)
    max_parents = fields.Integer(allow_none=True)
    min_children = fields.Integer(allow_none=True)
    max_children = fields.Integer(allow_none=True)


class ImageToSampleRelationModel(ItemRelation):
    image = fields.Nested(ItemSchemaModel)
    sample = fields.Nested(ItemSchemaModel)


class AnnotationToImageRelationModel(ItemRelation):
    annotation = fields.Nested(ItemSchemaModel)
    image = fields.Nested(ItemSchemaModel)


class ObservationToSampleRelationModel(ItemRelation):
    observation = fields.Nested(ItemSchemaModel)
    sample = fields.Nested(ItemSchemaModel)


class ObservationToImageRelationModel(ItemRelation):
    observation = fields.Nested(ItemSchemaModel)
    image = fields.Nested(ItemSchemaModel)


class ObservationToAnnotationRelationModel(ItemRelation):
    observation = fields.Nested(ItemSchemaModel)
    annotation = fields.Nested(ItemSchemaModel)


class SampleSchemaModel(ItemSchemaModel):
    children = fields.List(fields.Nested(SampleToSampleRelationModel))
    parents = fields.List(fields.Nested(SampleToSampleRelationModel))
    images = fields.List(fields.Nested(ImageToSampleRelationModel))
    observations = fields.List(fields.Nested(ObservationToSampleRelationModel))

    @post_load
    def post_load(self, data: Dict[str, Any], **kwargs):
        uid = data["uid"]
        return SampleSchema.get_by_uid(uid)


class ImageSchemaModel(ItemSchemaModel):
    samples = fields.List(fields.Nested(ImageToSampleRelationModel))
    annotations = fields.List(fields.Nested(AnnotationToImageRelationModel))
    observations = fields.List(fields.Nested(ObservationToImageRelationModel))

    @post_load
    def post_load(self, data: Dict[str, Any], **kwargs):
        uid = data["uid"]
        return ImageSchema.get_by_uid(uid)


class AnnotationSchemaModel(ItemSchemaModel):
    images = fields.List(fields.Nested(AnnotationToImageRelationModel))
    observations = fields.List(fields.Nested(ObservationToAnnotationRelationModel))

    @post_load
    def post_load(self, data: Dict[str, Any], **kwargs):
        uid = data["uid"]
        return AnnotationSchema.get_by_uid(uid)


class ObservationSchemaModel(ItemSchemaModel):
    samples = fields.List(fields.Nested(ObservationToSampleRelationModel))
    images = fields.List(fields.Nested(ObservationToImageRelationModel))
    annotations = fields.List(fields.Nested(ObservationToAnnotationRelationModel))

    @post_load
    def post_load(self, data: Dict[str, Any], **kwargs):
        uid = data["uid"]
        return ObservationSchema.get_by_uid(uid)


class ItemSchemaOneOfModel(BaseModel):
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

    def dump_many(self, item_schemas: Iterable[ItemSchema], **kwargs):
        return [self.dump(item_schema, **kwargs) for item_schema in item_schemas]

    def load(self, data: Dict[str, Any], **kwargs):
        item_value_type = ItemValueType(data["itemValueType"])
        if item_value_type == ItemValueType.SAMPLE:
            return SampleSchemaModel().load(data, **kwargs)
        if item_value_type == ItemValueType.IMAGE:
            return ImageSchemaModel().load(data, **kwargs)
        if item_value_type == ItemValueType.ANNOTATION:
            return AnnotationSchemaModel().load(data, **kwargs)
        if item_value_type == ItemValueType.OBSERVATION:
            return ObservationSchemaModel().load(data, **kwargs)
        raise ValueError(f"Unknown schema {item_value_type}.")
