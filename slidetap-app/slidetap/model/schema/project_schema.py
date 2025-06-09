from typing import Dict
from uuid import UUID

from slidetap.model.base_model import FrozenBaseModel
from slidetap.model.schema.attribute_schema import AnyAttributeSchema


class DatasetSchema(FrozenBaseModel):
    uid: UUID
    name: str
    display_name: str
    attributes: Dict[str, AnyAttributeSchema]


class ProjectSchema(FrozenBaseModel):
    uid: UUID
    name: str
    display_name: str
    attributes: Dict[str, AnyAttributeSchema]
