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

"""Tests for the DB-backed mapper resolution queries (Nexus #46 follow-up).

`get_exact_mapping_candidate` and `get_regex_mapping_items` replace the
in-memory `MapperExpressionIndex`: the exact/regex split now lives in the
`mapping_item.literal` column (set at write time, see
`tests/database/test_mapper.py`) instead of a per-process cache that could go
stale across the web and worker processes. These run against a real SQLite
database (not decoy mocks) since what they need to prove is the SQL itself:
the indexed literal lookup and the hits/uid ordering.
"""

from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine

from slidetap.config import DatabaseConfig
from slidetap.database import Base
from slidetap.model import Code, CodeAttribute
from slidetap.services import DatabaseService


@pytest.fixture()
def database_service(tmp_path: Path) -> DatabaseService:
    uri = f"sqlite:///{tmp_path / 'test.db'}"
    Base.metadata.create_all(bind=create_engine(uri))
    return DatabaseService(DatabaseConfig(uri, False))


def _attribute() -> CodeAttribute:
    return CodeAttribute(
        uid=uuid4(),
        schema_uid=uuid4(),
        original_value=Code(code="code", scheme="scheme", meaning="meaning"),
    )


@pytest.fixture()
def mapper_uid(database_service: DatabaseService) -> UUID:
    with database_service.get_session() as session:
        mapper = database_service.add_mapper(session, "test-mapper", uuid4(), uuid4())
        return mapper.uid


@pytest.mark.unittest
class TestGetExactMappingCandidate:
    def test_matches_by_literal(
        self, database_service: DatabaseService, mapper_uid: UUID
    ):
        with database_service.get_session() as session:
            database_service.add_mapping(
                session, mapper_uid, "^71854001$", _attribute()
            )
            database_service.add_mapping(
                session, mapper_uid, ".*resectie.*", _attribute()
            )

            candidate = database_service.get_exact_mapping_candidate(
                session, mapper_uid, "71854001"
            )

            assert candidate is not None
            assert candidate.expression == "^71854001$"

    def test_no_candidate_for_regex_only_value(
        self, database_service: DatabaseService, mapper_uid: UUID
    ):
        with database_service.get_session() as session:
            database_service.add_mapping(
                session, mapper_uid, ".*resectie.*", _attribute()
            )

            assert (
                database_service.get_exact_mapping_candidate(
                    session, mapper_uid, "resectie stuk"
                )
                is None
            )

    def test_colliding_literals_return_highest_hits(
        self, database_service: DatabaseService, mapper_uid: UUID
    ):
        # "^A$" and "A$" both classify to the literal "A" (start anchor is
        # implicit under re.match); the query must pick the higher-hit row
        # rather than an arbitrary one of the two.
        with database_service.get_session() as session:
            low_hits = database_service.add_mapping(
                session, mapper_uid, "^A$", _attribute()
            )
            high_hits = database_service.add_mapping(
                session, mapper_uid, "A$", _attribute()
            )
            low_hits.hits = 1
            high_hits.hits = 5

            candidate = database_service.get_exact_mapping_candidate(
                session, mapper_uid, "A"
            )

            assert candidate is not None
            assert candidate.uid == high_hits.uid

    def test_different_mappers_are_isolated(
        self, database_service: DatabaseService, mapper_uid: UUID
    ):
        with database_service.get_session() as session:
            other_mapper = database_service.add_mapper(
                session, "other-mapper", uuid4(), uuid4()
            )
            database_service.add_mapping(session, other_mapper.uid, "^A$", _attribute())

            assert (
                database_service.get_exact_mapping_candidate(session, mapper_uid, "A")
                is None
            )


@pytest.mark.unittest
class TestGetRegexMappingItems:
    def test_excludes_literal_expressions(
        self, database_service: DatabaseService, mapper_uid: UUID
    ):
        with database_service.get_session() as session:
            database_service.add_mapping(
                session, mapper_uid, "^71854001$", _attribute()
            )
            database_service.add_mapping(
                session, mapper_uid, ".*resectie.*", _attribute()
            )
            database_service.add_mapping(session, mapper_uid, "^HE[0-9]*", _attribute())

            regex_expressions = {
                item.expression
                for item in database_service.get_regex_mapping_items(
                    session, mapper_uid
                )
            }

            assert regex_expressions == {".*resectie.*", "^HE[0-9]*"}

    def test_ordered_by_hits_desc(
        self, database_service: DatabaseService, mapper_uid: UUID
    ):
        with database_service.get_session() as session:
            low = database_service.add_mapping(
                session, mapper_uid, ".*a.*", _attribute()
            )
            high = database_service.add_mapping(
                session, mapper_uid, ".*b.*", _attribute()
            )
            low.hits = 1
            high.hits = 9

            items = list(database_service.get_regex_mapping_items(session, mapper_uid))

            assert [item.uid for item in items] == [high.uid, low.uid]
