from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass
class Mapping:
    attribute_uid: UUID
    mappable_value: str
    mapper_name: Optional[str] = None
    mapper_uid: Optional[UUID] = None
    expression: Optional[str] = None
    value_uid: Optional[UUID] = None
