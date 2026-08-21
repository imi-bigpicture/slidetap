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

from uuid import uuid4

import pytest
from sqlalchemy import select
from test_item_service import TestAddSearchResultForAnExistingPatient, _uid

from slidetap.database import DatabaseSample
from slidetap.model import MetadataSearchResult


@pytest.mark.integration
class TestTwoImportsCreatingTheSameItem(TestAddSearchResultForAnExistingPatient):
    """Two cases of one patient imported at the same moment.

    Both results carry the patient, and the dedup lookup cannot see an insert
    the other transaction has not committed yet, so both find nothing and both
    insert. One of them is going to lose, and what it does about it is the
    difference between the dataset holding one patient and holding two.
    """

    def test_a_result_losing_the_race_uses_the_patient_the_winner_created(
        self,
        item_service,
        sqlite_database_service,
        schemas,
        dataset,
        batches,
        monkeypatch,
    ):
        # Arrange: the patient is in the dataset, put there by the import that
        # won the race.
        self._import(
            item_service,
            sqlite_database_service,
            schemas,
            dataset,
            batches[0],
            "PATIENT-1",
            "CASE-A",
        )
        # A second case of that patient, carrying a patient of its own with a
        # uid of its own -- what an importer generating fresh uuids per run
        # hands over, and the case the unique constraint rather than the
        # primary key has to catch.
        items = self._items(schemas, dataset, batches[0], "PATIENT-1", "CASE-B")
        items[4] = items[4].model_copy(update={"uid": uuid4()})
        result = MetadataSearchResult.succeeded(
            identifier="CASE-B",
            schema_uid=schemas["case"],
            items=items,  # type: ignore[arg-type]
            item_uid=_uid("CASE-B"),
        )
        # The lookup as the loser of the race sees it: at the moment it asks,
        # the winner's patient is inserted but not committed, so it is not
        # there to be found. Once only -- the retry is meant to see it.
        original = sqlite_database_service.get_items_by_identifier
        blinded = {"used": False}

        def blind_once(session, items):
            found = original(session, items)
            if blinded["used"]:
                return found
            blinded["used"] = True
            return {key: item for key, item in found.items() if key[2] != "PATIENT-1"}

        monkeypatch.setattr(
            sqlite_database_service, "get_items_by_identifier", blind_once
        )

        # Act
        with sqlite_database_service.get_session() as session:
            item_service.add_search_result(result, [], session=session)
            session.commit()

        # Assert
        assert blinded["used"], (
            "the lookup was never blinded, so this ran the ordinary dedup and "
            "not the race it is about"
        )
        with sqlite_database_service.get_session() as session:
            patients = (
                session.scalars(
                    select(DatabaseSample).filter_by(identifier="PATIENT-1")
                )
                .unique()
                .all()
            )
            assert len(patients) == 1, (
                "the import that lost the race should have used the patient "
                "the winner created rather than adding a second one"
            )
            assert {case.identifier for case in patients[0].children} == {
                "CASE-A",
                "CASE-B",
            }, "both cases should hang off the one patient"
