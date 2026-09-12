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

"""What a search item keeps of what its unit was imported from."""

from uuid import UUID, uuid4

import pytest

from slidetap.model import Dataset, Project
from slidetap.model.batch import BatchCreate
from slidetap.services import DatabaseService, MetadataSearchItemService


@pytest.mark.integration
class TestSearchItemParameters:
    @pytest.fixture()
    def search_item_service(
        self, sqlite_database_service: DatabaseService
    ) -> MetadataSearchItemService:
        return MetadataSearchItemService(sqlite_database_service)

    @pytest.fixture()
    def batch_uid(
        self,
        sqlite_database_service: DatabaseService,
        dataset: Dataset,
        project: Project,
    ) -> UUID:
        with sqlite_database_service.get_session() as session:
            sqlite_database_service.add_dataset(session, dataset)
            sqlite_database_service.add_project(session, project)
            return sqlite_database_service.add_batch(
                session, BatchCreate(name="batch", project_uid=project.uid)
            ).uid

    def test_what_the_unit_was_imported_from_is_given_back(
        self,
        search_item_service: MetadataSearchItemService,
        sqlite_database_service: DatabaseService,
        batch_uid: UUID,
    ):
        """The pseudonyms a document assigned a case are not in its id."""
        # Arrange
        parameters = {
            "caseId": "PL1234-20",
            "biologicalBeingPseudonym": "PATIENT_01",
            "casePseudonym": "CASE_01",
        }

        # Act
        with sqlite_database_service.get_session() as session:
            created = search_item_service.create(
                batch_uid=batch_uid,
                identifier="PL1234-20",
                schema_uid=uuid4(),
                search_parameters=parameters,
                session=session,
            )
            uid = created.uid
            session.commit()

        # Assert
        assert search_item_service.get(uid).search_parameters == parameters

    def test_what_the_unit_was_imported_from_is_not_serialized(
        self,
        search_item_service: MetadataSearchItemService,
        sqlite_database_service: DatabaseService,
        batch_uid: UUID,
    ):
        """Read off the row by the importer, not handed to the batch view."""
        # Arrange
        with sqlite_database_service.get_session() as session:
            created = search_item_service.create(
                batch_uid=batch_uid,
                identifier="PL1234-20",
                schema_uid=uuid4(),
                search_parameters={"casePseudonym": "CASE_01"},
                session=session,
            )
            uid = created.uid
            session.commit()

        # Act
        item = search_item_service.get(uid)

        # Assert
        assert item.search_parameters == {"casePseudonym": "CASE_01"}
        assert "searchParameters" not in item.model_dump(by_alias=True)

    def test_a_unit_its_identifier_describes_keeps_nothing(
        self,
        search_item_service: MetadataSearchItemService,
        sqlite_database_service: DatabaseService,
        batch_uid: UUID,
    ):
        # Arrange, Act
        with sqlite_database_service.get_session() as session:
            created = search_item_service.create(
                batch_uid=batch_uid,
                identifier="PL1234-20",
                schema_uid=uuid4(),
                session=session,
            )
            uid = created.uid
            session.commit()

        # Assert
        assert search_item_service.get(uid).search_parameters is None
