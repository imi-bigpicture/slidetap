from dataclasses import dataclass
from typing import Dict
from uuid import UUID

from slidetap.model.schema.attribute_schema import AttributeSchema


@dataclass(frozen=True)
class ProjectSchema:
    uid: UUID
    name: str
    display_name: str
    attributes: Dict[str, AttributeSchema]
