import dataclasses
import datetime
from dataclasses import dataclass
from typing import Dict, Optional
from uuid import UUID

from slidetap.model.attribute import Attribute
from slidetap.model.project_status import ProjectStatus


@dataclass
class Project:
    uid: UUID
    name: str
    root_schema_uid: UUID
    schema_uid: UUID
    dataset_uid: UUID
    created: datetime.datetime
    status: ProjectStatus = ProjectStatus.IN_PROGRESS
    valid_attributes: Optional[bool] = None
    attributes: Dict[str, Attribute] = dataclasses.field(default_factory=dict)
