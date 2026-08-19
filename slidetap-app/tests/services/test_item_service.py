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

"""Tests for `ItemService`.

Run against a real database, since what is being pinned is what a sequence of
writes leaves behind, which is the part that broke.
"""

from uuid import NAMESPACE_URL, UUID, uuid5

import pytest

from slidetap.model import (
    Dataset,
    Image,
    ImageFormat,
    MetadataSearchResult,
    Project,
    ReviewIssueSource,
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

# ---------------------------------------------------------------------------
# Adding what a metadata search found
# ---------------------------------------------------------------------------


def _uid(identifier: str) -> UUID:
    """A uid that is the same every time the same thing is loaded.

    What the metadata import does, so that re-importing a case finds the items
    it wrote last time rather than writing them again.
    """
    return uuid5(NAMESPACE_URL, identifier)


@pytest.mark.integration
class TestAddSearchResultForAnExistingPatient:
    """A case imported for a patient the dataset already holds.

    An import hands its items over child-first -- every child is added, and
    validated, before the parent that claims it -- so a case is written while
    it still has no patient, and it is the patient being added afterwards that
    tells it that it has one. When the patient is already in the dataset that
    add is a lookup rather than an insert, and the branch that does the lookup
    used to return before validating anything. The case kept the invalid it was
    given while the patient was not there yet, for good.

    Two cases of one patient are what the metadata import produces all the
    time, either inside a batch or across two of them, so this is the ordinary
    path and not a corner of it.
    """

    @pytest.fixture()
    def item_service(
        self, sqlite_database_service: DatabaseService, schema: RootSchema
    ) -> ItemService:
        """The real thing on a real database, unlike the mocked one above."""
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
        """The uids of the samples this builds a case out of, by name."""
        by_name = {sample.name: sample.uid for sample in schema.samples.values()}
        return {
            **{
                name: by_name[name]
                for name in ("slide", "block", "specimen", "case", "patient")
            },
            "image": next(iter(schema.images.values())).uid,
        }

    @pytest.fixture()
    def batches(
        self,
        sqlite_database_service: DatabaseService,
        dataset: Dataset,
        project: Project,
    ) -> list[UUID]:
        with sqlite_database_service.get_session() as session:
            sqlite_database_service.add_dataset(session, dataset)
            sqlite_database_service.add_project(session, project)
            return [
                sqlite_database_service.add_batch(
                    session, BatchCreate(name=name, project_uid=project.uid)
                ).uid
                for name in ("first", "second")
            ]

    @staticmethod
    def _items(
        schemas: dict[str, UUID],
        dataset: Dataset,
        batch_uid: UUID,
        patient_identifier: str,
        case_identifier: str,
    ) -> list[Sample | Image]:
        """One patient, one case, and the chain down to a scanned image.

        Yielded child-first with the hierarchy carried on the parent's
        ``children`` -- the order and the shape the BigPicture metadata import
        hands over, which is what makes the patient the last item to be added.
        """

        def sample(schema_uid: UUID, identifier: str, **children: object) -> Sample:
            return Sample(
                uid=_uid(identifier),
                identifier=identifier,
                dataset_uid=dataset.uid,
                batch_uid=batch_uid,
                schema_uid=schema_uid,
                **children,  # type: ignore[arg-type]
            )

        slide_id = f"{case_identifier}-1-A-1"
        block_id = f"{case_identifier}-1-A"
        specimen_id = f"{case_identifier}-1"
        return [
            sample(schemas["slide"], slide_id),
            sample(
                schemas["block"],
                block_id,
                children={schemas["slide"]: [_uid(slide_id)]},
            ),
            sample(
                schemas["specimen"],
                specimen_id,
                children={schemas["block"]: [_uid(block_id)]},
            ),
            sample(
                schemas["case"],
                case_identifier,
                children={schemas["specimen"]: [_uid(specimen_id)]},
            ),
            sample(
                schemas["patient"],
                patient_identifier,
                children={schemas["case"]: [_uid(case_identifier)]},
            ),
            # After the patient, as the importer's own image search produces it.
            Image(
                uid=_uid(f"{slide_id}-image"),
                identifier=f"{slide_id}-image",
                dataset_uid=dataset.uid,
                batch_uid=batch_uid,
                schema_uid=schemas["image"],
                samples={schemas["slide"]: [_uid(slide_id)]},
                format=ImageFormat.DICOM_WSI,
            ),
        ]

    def _import(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        schemas: dict[str, UUID],
        dataset: Dataset,
        batch_uid: UUID,
        patient_identifier: str,
        case_identifier: str,
    ) -> None:
        result = MetadataSearchResult.succeeded(
            identifier=case_identifier,
            schema_uid=schemas["case"],
            items=self._items(  # type: ignore[arg-type]
                schemas, dataset, batch_uid, patient_identifier, case_identifier
            ),
            item_uid=_uid(case_identifier),
        )
        with sqlite_database_service.get_session() as session:
            item_service.add_search_result(result, [], session=session)
            session.commit()

    def test_deleting_an_item_takes_what_was_raised_on_it_with_it(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        schemas: dict[str, UUID],
        dataset: Dataset,
        batches: list[UUID],
    ):
        """The failure this guards against: a batch that cannot drop what a
        curator took out of the project, because something was raised on it
        while it was still in and the record points at it."""
        # Arrange
        self._import(
            item_service,
            sqlite_database_service,
            schemas,
            dataset,
            batches[0],
            "PAT-1",
            "PL1234-20",
        )
        case_uid = _uid("PL1234-20")
        slide_uid = _uid("PL1234-20-1-A-1")
        with sqlite_database_service.get_session() as session:
            sqlite_database_service.add_review_issue(
                session,
                sqlite_database_service.get_item(session, slide_uid),
                sqlite_database_service.get_item(session, case_uid),
                "Not valid: relations",
                ReviewIssueSource.VALIDATION,
            )
            session.commit()

        # Act
        with sqlite_database_service.get_session() as session:
            session.delete(sqlite_database_service.get_item(session, slide_uid))
            session.commit()

        # Assert
        with sqlite_database_service.get_session() as session:
            assert (
                list(sqlite_database_service.get_review_issues(session, case_uid)) == []
            )

    @pytest.mark.parametrize(
        ("second_batch", "what"),
        [(False, "the same batch"), (True, "another batch")],
        ids=["same-batch", "other-batch"],
    )
    def test_second_case_of_a_patient_is_linked_and_valid(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        schemas: dict[str, UUID],
        dataset: Dataset,
        batches: list[UUID],
        second_batch: bool,
        what: str,
    ):
        # Arrange: the patient is in the dataset, brought in by their first case.
        self._import(
            item_service,
            sqlite_database_service,
            schemas,
            dataset,
            batches[0],
            "PATIENT-1",
            "CASE-A",
        )
        first = item_service.get_sample(_uid("CASE-A"))
        assert first.valid_relations, (
            "the first case of a new patient should come out valid -- if this "
            "fails the chain built by this test is incomplete, not the code"
        )

        # Act: a second case of the same patient, so the patient is found
        # rather than inserted.
        self._import(
            item_service,
            sqlite_database_service,
            schemas,
            dataset,
            batches[1] if second_batch else batches[0],
            "PATIENT-1",
            "CASE-B",
        )

        # Assert
        second = item_service.get_sample(_uid("CASE-B"))
        assert second.parents[schemas["patient"]] == [_uid("PATIENT-1")], (
            f"a case imported into {what} should hang from the patient already "
            f"in the dataset"
        )
        assert second.valid_relations, (
            f"a case imported into {what} for a patient already in the dataset "
            f"should not be left marked as having no patient"
        )

    def test_the_patient_holds_both_cases(
        self,
        item_service: ItemService,
        sqlite_database_service: DatabaseService,
        schemas: dict[str, UUID],
        dataset: Dataset,
        batches: list[UUID],
    ):
        # Arrange / Act
        for batch_uid, case_identifier in (
            (batches[0], "CASE-A"),
            (batches[1], "CASE-B"),
        ):
            self._import(
                item_service,
                sqlite_database_service,
                schemas,
                dataset,
                batch_uid,
                "PATIENT-1",
                case_identifier,
            )

        # Assert: one patient, not one per case, holding both.
        patient = item_service.get_sample(_uid("PATIENT-1"))
        assert sorted(patient.children[schemas["case"]]) == sorted(
            [_uid("CASE-A"), _uid("CASE-B")]
        )
        assert patient.valid_relations
