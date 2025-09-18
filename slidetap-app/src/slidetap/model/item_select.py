from typing import List, Optional
from uuid import UUID

from slidetap.model.base_model import CamelCaseBaseModel


class ItemSelect(CamelCaseBaseModel):
    select: bool
    comment: Optional[str] = None
    tags: Optional[List[UUID]] = None
    additive_tags: bool = False
