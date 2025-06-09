from uuid import UUID

from slidetap.model.base_model import FrozenBaseModel


class ItemReference(FrozenBaseModel):
    uid: UUID
    identifier: str
    # name: Optional[str]
    # schema_display_name: str
    # schema_uid: UUID
