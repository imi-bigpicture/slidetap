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

"""What reading a thumbnail writes."""

import datetime
from pathlib import Path
from uuid import UUID

import pytest
from decoy import Decoy
from decoy.matchers import Anything
from slidetap_example import ExampleSchema

from slidetap.database import (
    DatabaseBatch,
    DatabaseDataset,
    DatabaseImage,
    DatabaseProject,
)
from slidetap.model import BatchStatus, ImageFormat, ImageStatus
from slidetap.services import DatabaseService, ImageService, StorageService
from slidetap.services.image_service import ImageCache


def _add_pre_processed_image(
    database_service: DatabaseService, schema: ExampleSchema, folder_path: Path
) -> UUID:
    with database_service.get_session() as session:
        dataset = DatabaseDataset("dataset", schema.dataset.uid)
        session.add(dataset)
        project = DatabaseProject(
            "project",
            schema.uid,
            schema.project.uid,
            dataset.uid,
            datetime.datetime(2026, 10, 16),
        )
        session.add(project)
        batch = DatabaseBatch("batch", project.uid, datetime.datetime(2026, 10, 16))
        batch.status = BatchStatus.IMAGE_PRE_PROCESSING
        session.add(batch)
        session.flush()
        image = DatabaseImage(
            dataset_uid=dataset.uid,
            batch_uid=batch.uid,
            schema_uid=schema.image.uid,
            identifier="PL1234-20-1",
            format=ImageFormat.OTHER_WSI,
        )
        image.status = ImageStatus.PRE_PROCESSED
        image.folder_path = str(folder_path)
        session.add(image)
        session.commit()
        return image.uid


@pytest.mark.integration
class TestThumbnail:
    def test_a_thumbnail_made_on_request_is_not_stored(
        self,
        decoy: Decoy,
        monkeypatch: pytest.MonkeyPatch,
        sqlite_database_service: DatabaseService,
        schema: ExampleSchema,
        tmp_path: Path,
    ):
        """The failure this guards against: a thumbnail named after the image
        written into the outbox of a pseudonymised project on every request."""
        # Arrange
        image_uid = _add_pre_processed_image(sqlite_database_service, schema, tmp_path)
        storage_service = decoy.mock(cls=StorageService)
        image_service = ImageService(
            storage_service, sqlite_database_service, decoy.mock(cls=ImageCache)
        )
        monkeypatch.setattr(
            image_service,
            "_create_thumbnail",
            lambda image, width, height, format: b"thumbnail",
        )

        # Act
        thumbnail = image_service.get_thumbnail(image_uid, 64, 64, "png")

        # Assert
        assert thumbnail == b"thumbnail"
        decoy.verify(
            storage_service.store_thumbnail(
                Anything(), Anything(), Anything(), Anything()
            ),
            times=0,
        )
        decoy.verify(
            storage_service.store_thumbnail(Anything(), Anything(), Anything()),
            times=0,
        )
