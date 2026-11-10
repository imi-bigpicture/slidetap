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

"""When the status of a project, a batch and an image last changed, against a
real database.
"""

import datetime
from uuid import UUID

import pytest
from slidetap_example import ExampleSchema

from slidetap.database import DatabaseImage
from slidetap.model import (
    BatchCreate,
    BatchStatus,
    Dataset,
    ImageFormat,
    ImageStatus,
    Project,
    ProjectStatus,
)
from slidetap.services import DatabaseService

LONG_AGO = datetime.datetime(2000, 1, 1)


@pytest.fixture()
def batch_uid(
    stored_database_service: DatabaseService, dataset: Dataset, project: Project
) -> UUID:
    with stored_database_service.get_session() as session:
        stored_database_service.add_dataset(session, dataset)
        stored_database_service.add_project(session, project)
        batch = stored_database_service.add_batch(
            session, BatchCreate(name="batch", project_uid=project.uid)
        )
        session.commit()
        return batch.uid


@pytest.fixture()
def image_uid(
    stored_database_service: DatabaseService,
    schema: ExampleSchema,
    dataset: Dataset,
    batch_uid: UUID,
) -> UUID:
    with stored_database_service.get_session() as session:
        image = DatabaseImage(
            dataset.uid,
            batch_uid,
            schema.image_schema_uid,
            "image",
            ImageFormat.DICOM_WSI,
        )
        session.add(image)
        session.commit()
        return image.uid


@pytest.mark.integration
class TestStatusTracking:
    def test_a_batch_has_the_time_of_its_first_status(
        self, stored_database_service: DatabaseService, batch_uid: UUID
    ):
        with stored_database_service.get_session() as session:
            batch = stored_database_service.get_batch(session, batch_uid)
            assert batch.status_updated is not None

    def test_the_time_follows_a_change_of_the_status(
        self, stored_database_service: DatabaseService, batch_uid: UUID
    ):
        # Arrange
        with stored_database_service.get_session() as session:
            stored_database_service.get_batch(
                session, batch_uid
            ).status_updated = LONG_AGO
            session.commit()

        # Act
        with stored_database_service.get_session() as session:
            stored_database_service.get_batch(
                session, batch_uid
            ).status = BatchStatus.LOCKED
            session.commit()

        # Assert
        with stored_database_service.get_session() as session:
            batch = stored_database_service.get_batch(session, batch_uid)
            assert batch.status_updated is not None
            assert batch.status_updated > LONG_AGO
            assert batch.model.status_updated == batch.status_updated

    def test_the_same_status_set_again_keeps_the_time(
        self, stored_database_service: DatabaseService, batch_uid: UUID
    ):
        # Arrange
        with stored_database_service.get_session() as session:
            batch = stored_database_service.get_batch(session, batch_uid)
            batch.status_updated = LONG_AGO
            status = batch.status
            session.commit()

        # Act
        with stored_database_service.get_session() as session:
            stored_database_service.get_batch(session, batch_uid).status = status
            session.commit()

        # Assert
        with stored_database_service.get_session() as session:
            batch = stored_database_service.get_batch(session, batch_uid)
            assert batch.status_updated == LONG_AGO

    def test_the_time_follows_a_change_of_the_status_of_a_project(
        self,
        stored_database_service: DatabaseService,
        project: Project,
        batch_uid: UUID,
    ):
        # Arrange
        with stored_database_service.get_session() as session:
            stored_database_service.get_project(
                session, project.uid
            ).status_updated = LONG_AGO
            session.commit()

        # Act
        with stored_database_service.get_session() as session:
            stored_database_service.get_project(
                session, project.uid
            ).status = ProjectStatus.COMPLETED
            session.commit()

        # Assert
        with stored_database_service.get_session() as session:
            stored = stored_database_service.get_project(session, project.uid)
            assert stored.status_updated is not None
            assert stored.status_updated > LONG_AGO
            assert stored.model.status_updated == stored.status_updated

    def test_the_time_follows_a_change_of_the_status_of_an_image(
        self, stored_database_service: DatabaseService, image_uid: UUID
    ):
        """Without counting as a change to the image."""
        # Arrange
        with stored_database_service.get_session() as session:
            image = stored_database_service.get_image(session, image_uid)
            assert image.status_updated is not None
            image.status_updated = LONG_AGO
            last_changed = image.last_changed
            session.commit()

        # Act
        with stored_database_service.get_session() as session:
            stored_database_service.get_image(
                session, image_uid
            ).status = ImageStatus.DOWNLOADING
            session.commit()

        # Assert
        with stored_database_service.get_session() as session:
            image = stored_database_service.get_image(session, image_uid)
            assert image.status_updated is not None
            assert image.status_updated > LONG_AGO
            assert image.model.status_updated == image.status_updated
            assert image.last_changed == last_changed
