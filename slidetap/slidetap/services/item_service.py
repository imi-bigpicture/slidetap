"""Service for accessing attributes."""
from typing import Optional
from uuid import UUID

from slidetap.database import Item


class ItemService:
    """Item service should be used to interface with items"""

    def get(self, item_uid: UUID) -> Optional[Item]:
        return Item.get(item_uid)

    def select(self, item_uid: UUID, value: bool) -> Optional[Item]:
        item = Item.get(item_uid)
        if item is None:
            return None
        item.set_select(value)
        return item
