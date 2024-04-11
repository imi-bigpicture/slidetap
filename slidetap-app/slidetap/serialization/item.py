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
from uuid import UUID

from marshmallow import fields, post_load

from slidetap.database import (
    Annotation,
    AnnotationSchema,
    Image,
    ImageSchema,
    ItemSchema,
    Observation,
    ObservationSchema,
    Project,
    Sample,
    SampleSchema,
)
from slidetap.model import ImageStatus, ItemValueType
from slidetap.serialization.attribute import AttributeModel
from slidetap.serialization.base import BaseModel
from slidetap.serialization.common import (
    AttributeSimplifiedModel,
    ItemReferenceModel,
)
from slidetap.serialization.schema import ItemSchemaOneOfModel


class ItemBaseModel(BaseModel):
    uid = fields.UUID(allow_none=True)
    project_uid = fields.UUID(allow_none=True)
    identifier = fields.String()
    name = fields.String(allow_none=True)
    pseudonym = fields.String(allow_none=True)
    selected = fields.Boolean(load_default=True)
    valid = fields.Boolean()
    item_value_type = fields.Enum(ItemValueType, by_value=True)


class ItemDetailsModel(ItemBaseModel):
    valid_attributes = fields.Boolean()
    valid_relations = fields.Boolean()
    schema = fields.Nested(ItemSchemaOneOfModel)
    attributes = fields.Dict(keys=fields.String(), values=fields.Nested(AttributeModel))


class ItemModel(ItemBaseModel):
    attributes = fields.Dict(
        keys=fields.String(),
        values=fields.Nested(AttributeSimplifiedModel),
        attribute="display_in_table_attributes",
    )


class SampleDetailsModel(ItemDetailsModel):
    parents = fields.List(fields.Nested(ItemReferenceModel))
    children = fields.List(fields.Nested(ItemReferenceModel))
    images = fields.List(fields.Nested(ItemReferenceModel))
    observations = fields.List(fields.Nested(ItemReferenceModel))

    @post_load
    def post_load(self, data: Dict[str, Any], **kwargs) -> Sample:
        uid = data.get("uid", None)
        if uid is None:
            project = Project.get(self.context["project_uid"])
            selected = data.pop("selected", None)
            children = data.pop("children")
            parents = data.pop("parents")
            schema = data.pop("schema")
            name = data.pop("name")
            identifier = data.pop("identifier")
            pseudonym = data.pop("pseudonym")
            attributes = data.pop("attributes")
            sample = Sample(
                project=project,
                name=name,
                schema=schema,
                parents=parents,
                attributes=attributes,
                identifier=identifier,
                pseudonym=pseudonym,
                selected=selected,
                add=False,
                commit=False,
            )
            sample.set_children(children, commit=False)
            return sample
        if not isinstance(uid, UUID):
            uid = UUID(uid)
        sample = Sample.get(uid)
        sample.set_name(data["name"], commit=False)
        sample.set_select(data["selected"], commit=False)
        sample.set_children(data["children"], commit=False)
        sample.set_parents(data["parents"], commit=False)
        sample.set_attributes(data["attributes"])
        sample.commit()
        return sample


class ImageDetailsModel(ItemDetailsModel):
    status = fields.Enum(ImageStatus, by_value=True)
    status_message = fields.String()
    samples = fields.List(fields.Nested(ItemReferenceModel))

    @post_load
    def post_load(self, data: Dict[str, Any], **kwargs) -> Image:
        uid = data.get("uid", None)
        if uid is None:
            raise NotImplementedError()
        if not isinstance(uid, UUID):
            uid = UUID(uid)
        image = Image.get(uid)
        image.set_name(data["name"], commit=False)
        image.set_select(data["selected"], commit=False)
        image.set_samples(data["samples"], commit=False)
        image.set_attributes(data["attributes"])
        image.commit()
        return image


class AnnotationDetailsModel(ItemDetailsModel):
    image = fields.Nested(ItemReferenceModel)

    @post_load
    def post_load(self, data: Dict[str, Any], **kwargs) -> Annotation:
        uid = data.get("uid", None)
        if uid is None:
            raise NotImplementedError()
        if not isinstance(uid, UUID):
            uid = UUID(uid)
        annotation = Annotation.get(uid)
        annotation.set_name(data["name"], commit=False)
        annotation.set_select(data["selected"], commit=False)
        annotation.set_image(data["samples"], commit=False)
        annotation.set_attributes(data["attributes"])
        annotation.commit()
        return annotation


class ObservationDetailsModel(ItemDetailsModel):
    item = fields.Nested(ItemReferenceModel)

    @post_load
    def post_load(self, data: Dict[str, Any], **kwargs) -> Observation:
        uid = data.get("uid", None)
        if uid is None:
            raise NotImplementedError()
        if not isinstance(uid, UUID):
            uid = UUID(uid)
        observation = Observation.get(uid)
        observation.set_name(data["name"], commit=False)
        observation.set_select(data["selected"], commit=False)
        observation.set_item(data["item"], commit=False)
        observation.set_attributes(data["attributes"])
        observation.commit()
        return observation


class SampleModel(ItemModel):
    pass


class ImageModel(ItemModel):
    status = fields.Enum(ImageStatus, by_value=True)
    status_message = fields.String()


class AnnotationModel(ItemModel):
    pass


class ObservationModel(ItemModel):
    pass


class ItemModelFactory:
    def create(self, item_schema: ItemSchema):
        if isinstance(item_schema, SampleSchema):
            return SampleDetailsModel
        if isinstance(item_schema, ImageSchema):
            return ImageDetailsModel
        if isinstance(item_schema, AnnotationSchema):
            return AnnotationDetailsModel
        if isinstance(item_schema, ObservationSchema):
            return ObservationDetailsModel
        raise ValueError(f"Unknown item schema {item_schema}.")

    def create_simplified(self, item_schema: ItemSchema):
        if isinstance(item_schema, SampleSchema):
            return SampleModel
        if isinstance(item_schema, ImageSchema):
            return ImageModel
        if isinstance(item_schema, AnnotationSchema):
            return AnnotationModel
        if isinstance(item_schema, ObservationSchema):
            return ObservationModel
        raise ValueError(f"Unknown item schema {item_schema}.")
