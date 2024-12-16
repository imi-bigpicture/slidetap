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

from typing import Any, Dict

from marshmallow import fields, post_load

from slidetap.model import ImageStatus, ItemValueType
from slidetap.model.item import Annotation, Image, Item, Observation, Sample
from slidetap.serialization.attribute import AttributeDictField
from slidetap.serialization.base import BaseModel


class ItemBaseModel(BaseModel):
    uid = fields.UUID(allow_none=True)
    project_uid = fields.UUID(allow_none=True)
    identifier = fields.String()
    name = fields.String(allow_none=True)
    pseudonym = fields.String(allow_none=True)
    selected = fields.Boolean(load_default=True)
    item_value_type = fields.Enum(ItemValueType, by_value=True)
    valid = fields.Boolean()
    valid_attributes = fields.Boolean()
    valid_relations = fields.Boolean()
    schema_uid = fields.UUID()
    attributes = AttributeDictField()


class SampleModel(ItemBaseModel):
    parents = fields.List(fields.UUID())
    children = fields.List(fields.UUID())
    images = fields.List(fields.UUID())
    observations = fields.List(fields.UUID())

    @post_load
    def post_load(self, data: Dict[str, Any], **kwargs) -> Sample:
        return Sample(**data)


class ImageModel(ItemBaseModel):
    status = fields.Enum(ImageStatus, by_value=True)
    status_message = fields.String()
    samples = fields.List(fields.UUID())

    @post_load
    def post_load(self, data: Dict[str, Any], **kwargs) -> Image:
        return Image(**data)


class AnnotationModel(ItemBaseModel):
    image = fields.UUID()
    observations = fields.List(fields.UUID())

    @post_load
    def post_load(self, data: Dict[str, Any], **kwargs) -> Annotation:
        return Annotation(**data)


class ObservationModel(ItemBaseModel):
    image = fields.UUID()
    sample = fields.UUID()
    annotation = fields.UUID()

    @post_load
    def post_load(self, data: Dict[str, Any], **kwargs) -> Observation:
        return Observation(**data)


class ItemModel(BaseModel):
    def load(self, data: Dict[str, Any], **kwargs) -> Item:
        item_value_type = data.get("item_value_type")
        if item_value_type == ItemValueType.SAMPLE:
            return SampleModel(exclude=self.exclude).load(data, **kwargs)  # type: ignore
        elif item_value_type == ItemValueType.IMAGE:
            return ImageModel(exclude=self.exclude).load(data, **kwargs)  # type: ignore
        elif item_value_type == ItemValueType.ANNOTATION:
            return AnnotationModel(exclude=self.exclude).load(data, **kwargs)  # type: ignore
        elif item_value_type == ItemValueType.OBSERVATION:
            return ObservationModel(exclude=self.exclude).load(data, **kwargs)  # type: ignore
        raise ValueError(f"Unknown item value type {item_value_type}")

    def dump(self, item: Item, **kwargs):
        model = self.create_model_for_item(item)
        return model.dump(item, **kwargs)

    @classmethod
    def create_model_for_item(cls, item: Item, **kwargs) -> ItemBaseModel:
        if isinstance(item, Sample):
            return SampleModel(**kwargs)
        elif isinstance(item, Image):
            return ImageModel(**kwargs)
        elif isinstance(item, Annotation):
            return AnnotationModel(**kwargs)
        elif isinstance(item, Observation):
            return ObservationModel(**kwargs)
        raise ValueError(f"Unknown item {item}")
