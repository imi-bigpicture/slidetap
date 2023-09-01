from slides.database.schema.item_schema import (
    AnnotationSchema,
    ImageSchema,
    ItemSchema,
    ObservationSchema,
    SampleSchema,
)
from slides.model.image_status import ImageStatus
from slides.model.item_value_type import ItemValueType
from slides.serialization.base import BaseModel
from marshmallow import fields
from slides.serialization.common import (
    AttributeSimplifiedModel,
    ItemReferenceModel,
)
from slides.serialization.attribute import AttributeModel
from slides.serialization.schema import (
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
    uid = fields.UUID()
    name = fields.String()
    selected = fields.Boolean()
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
    observed_on = fields.Nested(ItemReferenceModel)


class SampleModel(SampleBaseModel, ItemModelFullAttributesMixin):
    pass


class SampleSimplifiedModel(SampleBaseModel, ItemModelSimplifiedAttributesMixin):
    pass


class ImageModel(ImageBaseModel, ItemModelFullAttributesMixin):
    pass


class ImageSimplifiedModel(ImageModel, ItemModelSimplifiedAttributesMixin):
    pass


class AnnotationModel(AnnotationBaseModel, ItemModelFullAttributesMixin):
    pass


class AnnotationSimplifiedModel(AnnotationModel, ItemModelSimplifiedAttributesMixin):
    pass


class ObservationModel(ObservationBaseModel, ItemModelFullAttributesMixin):
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
