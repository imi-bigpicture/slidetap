#    Copyright 2026 SECTRA AB
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

"""Stamp when the status of a project, a batch or an image last changed.

Done by attribute listeners, registered by `register`, so that every place that
sets a status is covered.
"""

import datetime
from typing import Any

from sqlalchemy import event

from slidetap.database.item import DatabaseImage
from slidetap.database.project import DatabaseBatch, DatabaseProject


def _stamp(target: Any, value: Any, oldvalue: Any, initiator: Any) -> None:
    """Stamp `status_updated` where the status changes, including when first
    set."""
    if value != oldvalue:
        target.status_updated = datetime.datetime.now()


def register() -> None:
    """Stamp status changes of projects, batches and images.

    Called when the database package is imported; calling it again does nothing.
    """
    for tracked in (DatabaseProject, DatabaseBatch, DatabaseImage):
        if not event.contains(tracked.status, "set", _stamp):
            event.listen(tracked.status, "set", _stamp)
