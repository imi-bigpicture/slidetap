#    Copyright 2024 SECTRA AB
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""Batch model representing a group of items."""

import datetime
from uuid import UUID

from slidetap.model.base_model import CamelCaseBaseModel
from slidetap.model.batch_status import BatchStatus


class Batch(CamelCaseBaseModel):
    """A batch of items within a project."""

    uid: UUID
    name: str
    status: BatchStatus
    project_uid: UUID
    is_default: bool
    created: datetime.datetime
