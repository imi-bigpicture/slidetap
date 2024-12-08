from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class ItemReference:
    uid: UUID
    identifier: str
    name: Optional[str]
    schema_display_name: str
    schema_uid: UUID
