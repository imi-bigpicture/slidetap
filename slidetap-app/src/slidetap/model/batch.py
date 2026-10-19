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


class BatchCreate(CamelCaseBaseModel):
    """Data needed to create a new batch."""

    name: str
    project_uid: UUID
    is_default: bool = False


class Batch(CamelCaseBaseModel):
    """A batch of items within a project."""

    uid: UUID
    name: str
    status: BatchStatus
    project_uid: UUID
    is_default: bool
    created: datetime.datetime
    status_message: str | None = None
    """Why the batch is in its current status, if it failed."""


class BatchStoringProgress(CamelCaseBaseModel):
    """How far storing the images of a batch to the outbox has come.

    Counted over the selected images the batch stores: those processed, being
    stored, stored, or failed to store.
    """

    batch_uid: UUID
    total: int
    """How many images the batch stores."""
    stored: int
    """How many of them are in the outbox."""
    failed: int
    """How many failed to store, and wait to be retried or taken out."""
