from typing import Any, Dict
from uuid import UUID
from slidetap.database import Sample, attribute
from slidetap.database import (
    AnnotationSchema,
    ImageSchema,
    ItemSchema,
    ObservationSchema,
    SampleSchema,
    db,
)
from slidetap.database.project import Annotation, Image, Observation, Project
from slidetap.model.image_status import ImageStatus
from slidetap.model.item_value_type import ItemValueType
from slidetap.serialization.base import BaseModel
from marshmallow import fields, post_load
from slidetap.serialization.common import (
    AttributeSimplifiedModel,
    ItemReferenceModel,
)
from slidetap.serialization.attribute import AttributeModel
from slidetap.serialization.schema import (
    ItemSchemaModel,
)


class ItemModelFullAttributesMixin(BaseModel):
    attributes = fields.Dict(keys=fields.String(), values=fields.Nested(AttributeModel))


class ItemModelSimplifiedAttributesMixin(BaseModel):
    attributes = fields.Dict(
        keys=fields.String(),
        values=fields.Nested(AttributeSimplifiedModel),
    )


class ItemBaseModel(BaseModel):
    uid = fields.UUID(allow_none=True)
    name = fields.String()
    selected = fields.Boolean(allow_none=True)
    schema = fields.Nested(ItemSchemaModel)
    item_value_type = fields.Enum(ItemValueType, by_value=True)


class SampleBaseModel(ItemBaseModel):
    parents = fields.List(fields.Nested(ItemReferenceModel))
    children = fields.List(fields.Nested(ItemReferenceModel))


class ImageBaseModel(ItemBaseModel):
    status = fields.Enum(ImageStatus, by_value=True)
    samples = fields.List(fields.Nested(ItemReferenceModel))


class AnnotationBaseModel(ItemBaseModel):
    image = fields.Nested(ItemReferenceModel)


class ObservationBaseModel(ItemBaseModel):
    item = fields.Nested(ItemReferenceModel)


class SampleModel(SampleBaseModel, ItemModelFullAttributesMixin):
    @post_load
    def post_load(self, data: Dict[str, Any], **kwargs) -> Sample:
        uid = data.get("uid", None)
        if uid is None:
            project = Project.get_project(self.context["project_uid"])
            assert project is not None
            selected = data.pop("selected", None)
            children = data.pop("children")
            parents = data.pop("parents")
            schema = data.pop("schema")
            name = data.pop("name")
            attributes = data.pop("attributes")
            sample = Sample(
                project=project,
                name=name,
                sample_schema=schema,
                parents=parents,
                attributes=attributes,
                add=False,
                commit=False,
            )
            sample.set_children(children, commit=False)
            db.session.commit()
            return sample
        if not isinstance(uid, UUID):
            uid = UUID(uid)
        sample = Sample.get(uid)
        sample.set_name(data["name"], commit=False)
        sample.set_select(data["selected"], commit=False)
        sample.set_children(data["children"], commit=False)
        sample.set_parents(data["parents"], commit=False)
        sample.set_attributes(data["attributes"])
        db.session.commit()
        return sample


class ImageModel(ImageBaseModel, ItemModelFullAttributesMixin):
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
        db.session.commit()
        return image


class AnnotationModel(AnnotationBaseModel, ItemModelFullAttributesMixin):
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
        db.session.commit()
        return annotation


class ObservationModel(ObservationBaseModel, ItemModelFullAttributesMixin):
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
        db.session.commit()
        return observation


class SampleSimplifiedModel(SampleBaseModel, ItemModelSimplifiedAttributesMixin):
    pass


class ImageSimplifiedModel(ImageBaseModel, ItemModelSimplifiedAttributesMixin):
    pass


class AnnotationSimplifiedModel(
    AnnotationBaseModel, ItemModelSimplifiedAttributesMixin
):
    pass


class ObservationSimplifiedModel(
    ObservationBaseModel, ItemModelSimplifiedAttributesMixin
):
    pass


class ItemModelFactory:
    def create(self, item_schema: ItemSchema):
        if isinstance(item_schema, SampleSchema):
            return SampleModel
        if isinstance(item_schema, ImageSchema):
            return ImageModel
        if isinstance(item_schema, AnnotationSchema):
            return AnnotationModel
        if isinstance(item_schema, ObservationSchema):
            return ObservationModel
        raise ValueError(f"Unknown item schema {item_schema}.")

    def create_simplified(self, item_schema: ItemSchema):
        if isinstance(item_schema, SampleSchema):
            return SampleSimplifiedModel
        if isinstance(item_schema, ImageSchema):
            return ImageSimplifiedModel
        if isinstance(item_schema, AnnotationSchema):
            return AnnotationSimplifiedModel
        if isinstance(item_schema, ObservationSchema):
            return ObservationSimplifiedModel
        raise ValueError(f"Unknown item schema {item_schema}.")
