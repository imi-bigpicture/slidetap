from dataclasses import dataclass
import datetime
from uuid import UUID

from slidetap.model.batch_status import BatchStatus


@dataclass
class Batch:
    uid: UUID
    name: str
    status: BatchStatus
    project_uid: UUID
    is_default: bool
    created: datetime.datetime
