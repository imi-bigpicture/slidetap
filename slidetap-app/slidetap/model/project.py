from dataclasses import dataclass
from typing import Dict, Optional
from uuid import UUID

from slidetap.model.attribute import Attribute
from slidetap.model.project_status import ProjectStatus


@dataclass(frozen=True)
class Project:
    uid: UUID
    name: str
    status: ProjectStatus
    valid_attributes: Optional[bool]
    schema_uid: UUID
    attributes: Dict[str, Attribute]
