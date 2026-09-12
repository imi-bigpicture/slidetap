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

"""What happens when two items are given the same pseudonym."""

import logging
from uuid import NAMESPACE_URL, UUID, uuid5

import pytest

from slidetap.database import NotAllowedActionError
from slidetap.model import (
    Dataset,
    MetadataSearchResult,
    Project,
    RootSchema,
    Sample,
)
from slidetap.model.batch import BatchCreate
from slidetap.services import (
    AttributeService,
    DatabaseService,
    ItemService,
    MapperService,
    ReviewService,
    SchemaService,
    TagService,
    ValidationService,
)


def _uid(identifier: str) -> UUID:
    return uuid5(NAMESPACE_URL, identifier)


@pytest.mark.integration
class TestPseudonymsAreNotShared:
    """A pseudonym stands for one item of a schema in a dataset."""

    @pytest.fixture()
    def item_service(
        self, sqlite_database_service: DatabaseService, schema: RootSchema
    ) -> ItemService:
        schema_service = SchemaService(schema)
        validation_service = ValidationService(schema_service, sqlite_database_service)
        review_service = ReviewService(
            schema_service, validation_service, sqlite_database_service
        )
        attribute_service = AttributeService(
            schema_service, validation_service, sqlite_database_service, review_service
        )
        return ItemService(
            attribute_service,
            TagService(sqlite_database_service),
            MapperService(
                attribute_service,
                validation_service,
                schema_service,
                sqlite_database_service,
                review_service,
            ),
            schema_service,
            validation_service,
            sqlite_database_service,
            review_service,
        )

    @pytest.fixture()
    def schemas(self, schema: RootSchema) -> dict[str, UUID]:
        by_name = {sample.name: sample.uid for sample in schema.samples.values()}
        return {name: by_name[name] for name in ("case", "patient")}

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

    @staticmethod
    def _sample(
        schema_uid: UUID,
        identifier: str,
        pseudonym: str | None,
        dataset: Dataset,
        batch_uid: UUID,
    ) -> Sample:
        return Sample(
            uid=_uid(identifier),
            identifier=identifier,
            pseudonym=pseudonym,
            dataset_uid=dataset.uid,
            batch_uid=batch_uid,
            schema_uid=schema_uid,
        )

    def _add(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        schema_uid: UUID,
        *items: Sample,
    ) -> None:
        result = MetadataSearchResult.succeeded(
            identifier=items[0].identifier,
            schema_uid=schema_uid,
            items=list(items),  # type: ignore[arg-type]
            item_uid=items[0].uid,
        )
        with sqlite_database_service.get_session() as session:
            item_service.add_search_result(result, [], session=session)
            session.commit()

    def test_a_pseudonym_another_item_of_the_schema_holds_is_refused(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        schemas: dict[str, UUID],
        dataset: Dataset,
        batch_uid: UUID,
        caplog: pytest.LogCaptureFixture,
    ):
        # Arrange
        self._add(
            item_service,
            sqlite_database_service,
            schemas["case"],
            self._sample(schemas["case"], "CASE-A", "PSEUDO-1", dataset, batch_uid),
        )

        # Act
        with (
            caplog.at_level(logging.ERROR),
            pytest.raises(NotAllowedActionError) as raised,
        ):
            self._add(
                item_service,
                sqlite_database_service,
                schemas["case"],
                self._sample(schemas["case"], "CASE-B", "PSEUDO-1", dataset, batch_uid),
            )

        # Assert
        assert "PSEUDO-1" in str(raised.value)
        assert "CASE-A" not in str(raised.value), (
            "the refusal is handed to every client of the batch, so what else "
            "the pseudonym is known by does not belong in it"
        )
        assert "CASE-A" in caplog.text
        assert item_service.get_optional_sample(_uid("CASE-B")) is None, (
            "the case that could not have the pseudonym should not be stored"
        )

    def test_the_same_pseudonym_under_another_schema_is_stored(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        schemas: dict[str, UUID],
        dataset: Dataset,
        batch_uid: UUID,
    ):
        """Uniqueness is per schema."""
        # Arrange
        self._add(
            item_service,
            sqlite_database_service,
            schemas["case"],
            self._sample(schemas["case"], "CASE-A", "PSEUDO-1", dataset, batch_uid),
        )

        # Act
        self._add(
            item_service,
            sqlite_database_service,
            schemas["patient"],
            self._sample(
                schemas["patient"], "PATIENT-1", "PSEUDO-1", dataset, batch_uid
            ),
        )

        # Assert
        patient = item_service.get_optional_sample(_uid("PATIENT-1"))
        assert patient is not None and patient.pseudonym == "PSEUDO-1"

    def test_two_items_of_one_result_cannot_share_a_pseudonym(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        schemas: dict[str, UUID],
        dataset: Dataset,
        batch_uid: UUID,
    ):
        """The collision is with what the unit has just created."""
        # Arrange
        first = self._sample(schemas["case"], "CASE-A", "PSEUDO-1", dataset, batch_uid)
        second = self._sample(schemas["case"], "CASE-B", "PSEUDO-1", dataset, batch_uid)

        # Act
        with pytest.raises(NotAllowedActionError) as raised:
            self._add(
                item_service, sqlite_database_service, schemas["case"], first, second
            )

        # Assert
        assert "PSEUDO-1" in str(raised.value)
        assert item_service.get_optional_sample(_uid("CASE-A")) is None, (
            "a result stored whole or not at all should leave nothing behind"
        )

    def test_an_item_without_a_pseudonym_collides_with_nothing(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        schemas: dict[str, UUID],
        dataset: Dataset,
        batch_uid: UUID,
    ):
        """Two items with no pseudonym are not two items sharing one."""
        # Arrange
        first = self._sample(schemas["case"], "CASE-A", None, dataset, batch_uid)
        second = self._sample(schemas["case"], "CASE-B", None, dataset, batch_uid)

        # Act
        self._add(item_service, sqlite_database_service, schemas["case"], first)
        self._add(item_service, sqlite_database_service, schemas["case"], second)

        # Assert
        assert item_service.get_optional_sample(_uid("CASE-B")) is not None
