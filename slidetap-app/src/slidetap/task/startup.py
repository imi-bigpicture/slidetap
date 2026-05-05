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

"""Recovery of dead processing on Celery worker startup."""

import logging
from typing import List, Tuple
from uuid import UUID

from sqlalchemy import select

from slidetap.database import DatabaseBatch
from slidetap.model import ImageStatus
from slidetap.model.batch_status import BatchStatus
from slidetap.services import DatabaseService, StorageService
from slidetap.task.heartbeat import ImageHeartbeat
from slidetap.task.tasks import (
    download_and_pre_process_image,
    post_process_image,
    store_batch_images_to_outbox,
)

logger = logging.getLogger(__name__)


class StartupRecovery:
    """Detect and recover images/batches stuck from a killed worker."""

    def __init__(
        self,
        database_service: DatabaseService,
        storage_service: StorageService,
    ):
        self._database_service = database_service
        self._storage_service = storage_service

    def recover(self) -> None:
        """Recover stuck images and batches on worker startup.

        Resets stuck images whose heartbeat has gone stale and re-dispatches them.
        """
        self._recover_stuck_images()
        self._recover_stuck_batches()

    def _recover_stuck_images(self) -> None:
        """Reset images stuck in PRE_PROCESSING or POST_PROCESSING and re-dispatch."""
        to_redispatch: List[Tuple[UUID, ImageStatus]] = []

        with self._database_service.get_session() as session:
            stuck_images = self._database_service.get_stuck_processing_images(
                session, ImageHeartbeat.STALE_AFTER_SECONDS
            )

            if not stuck_images:
                logger.info("No stuck images found on startup.")
                return

            for image in stuck_images:
                old_status = image.status
                task_id = image.processing_task_id

                if old_status == ImageStatus.DOWNLOADING:
                    image.status = ImageStatus.NOT_STARTED
                elif old_status == ImageStatus.PRE_PROCESSING:
                    image.status = ImageStatus.DOWNLOADED
                else:
                    image.status = ImageStatus.PRE_PROCESSED

                image.processing_started_at = None
                image.processing_task_id = None
                image.last_heartbeat_at = None

                to_redispatch.append((image.uid, old_status))

                logger.warning(
                    f"Reset image {image.uid} from {old_status.name} "
                    f"to {image.status.name} (stale heartbeat, dead task_id={task_id})"
                )

                if task_id is not None and image.batch is not None:
                    try:
                        project = image.batch.project.model
                        self._storage_service.cleanup_processing_task(
                            project, task_id
                        )
                    except Exception:
                        logger.error(
                            f"Failed to cleanup processing task {task_id} "
                            f"for image {image.uid}",
                            exc_info=True,
                        )

        logger.warning(
            f"Recovering {len(to_redispatch)} stuck image(s) on startup."
        )

        for image_uid, original_status in to_redispatch:
            if original_status in (
                ImageStatus.DOWNLOADING,
                ImageStatus.PRE_PROCESSING,
            ):
                logger.info(
                    f"Re-dispatching download_and_pre_process_image for {image_uid}"
                )
                download_and_pre_process_image.delay(image_uid)  # type: ignore
            else:
                logger.info(f"Re-dispatching post_process_image for {image_uid}")
                post_process_image.delay(image_uid)  # type: ignore

    def _recover_stuck_batches(self) -> None:
        """Re-dispatch store_batch_images_to_outbox for batches stuck in IMAGE_STORING."""
        with self._database_service.get_session(commit=False) as session:
            stuck_batch_uids: List[UUID] = [
                row.uid
                for row in session.execute(
                    select(DatabaseBatch.uid).where(
                        DatabaseBatch.status == BatchStatus.IMAGE_STORING
                    )
                ).all()
            ]

        if not stuck_batch_uids:
            logger.info("No stuck batches found on startup.")
            return

        logger.warning(
            f"Found {len(stuck_batch_uids)} batch(es) stuck in IMAGE_STORING."
        )

        for batch_uid in stuck_batch_uids:
            logger.info(
                f"Re-dispatching store_batch_images_to_outbox for batch {batch_uid}"
            )
            store_batch_images_to_outbox.delay(batch_uid)  # type: ignore
