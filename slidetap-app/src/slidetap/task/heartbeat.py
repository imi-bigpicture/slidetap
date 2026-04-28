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

"""Background heartbeat for long-running Celery tasks.

A daemon thread updates ``last_heartbeat_at`` on the claimed image row so an
external sweeper can detect tasks killed by SIGKILL/OOM, which can't run
cleanup code themselves.
"""

import logging
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator
from uuid import UUID

from sqlalchemy import update

from slidetap.database import DatabaseImage
from slidetap.services import DatabaseService

logger = logging.getLogger(__name__)


class ImageHeartbeat:
    """Provides per-image heartbeat scopes for processing tasks."""

    INTERVAL_SECONDS: float = 60.0
    STALE_AFTER_SECONDS: float = 5 * 60

    def __init__(self, database_service: DatabaseService):
        self._database_service = database_service

    @contextmanager
    def track(
        self,
        image_uid: UUID,
        interval_seconds: float = INTERVAL_SECONDS,
    ) -> Iterator[None]:
        stop = threading.Event()
        thread = threading.Thread(
            target=self._loop,
            args=(image_uid, interval_seconds, stop),
            name=f"heartbeat-{image_uid}",
            daemon=True,
        )
        thread.start()
        try:
            yield
        finally:
            stop.set()
            thread.join(timeout=5.0)

    def _loop(
        self,
        image_uid: UUID,
        interval_seconds: float,
        stop: threading.Event,
    ) -> None:
        while not stop.wait(interval_seconds):
            try:
                with self._database_service.get_session() as session:
                    session.execute(
                        update(DatabaseImage)
                        .where(DatabaseImage.uid == image_uid)
                        .values(last_heartbeat_at=datetime.now(timezone.utc))
                    )
            except Exception:
                logger.warning(
                    f"Heartbeat update failed for image {image_uid}", exc_info=True
                )
