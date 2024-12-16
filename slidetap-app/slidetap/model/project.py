import dataclasses
from dataclasses import dataclass
from typing import Dict, Optional
from uuid import UUID

from slidetap.model.attribute import Attribute
from slidetap.model.project_status import ProjectStatus


@dataclass(frozen=True)
class Project:
    uid: UUID
    name: str
    schema_uid: UUID
    status: ProjectStatus = ProjectStatus.INITIALIZED
    valid_attributes: Optional[bool] = None
    attributes: Dict[str, Attribute] = dataclasses.field(default_factory=dict)
