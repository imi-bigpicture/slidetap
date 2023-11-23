from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass
class Mapping:
    """Mapping for an attribute

    Parameters
    ----------
    attribute_uid: UUID
        UID of the attribute.
    mappable_value: str
        Value that can be mapped.
    mapper_name: Optional[str]
        Name of the mapper that has mapped the attribute, if any.
    mapper_uid: Optional[UUID]
        UID of the mapper that has mapped the attribute, if any.
    expression: Optional[str]
        Expression in mapper that matched the mappable value of he attribute, if any.
    value_uid: Optional[UUID]
        UID of the attribute that was mapped, if any.

    """

    attribute_uid: UUID
    mappable_value: str
    mapper_name: Optional[str] = None
    mapper_uid: Optional[UUID] = None
    expression: Optional[str] = None
    value_uid: Optional[UUID] = None
