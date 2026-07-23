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

"""Tests for the mapper resolver fast path (Nexus #46).

Covers `MapperService._resolve_expression`: combining the DB's exact-literal
lookup (`DatabaseService.get_exact_mapping_candidate`) with the small set of
genuinely regex-shaped expressions (`get_regex_mapping_items`) to pick the
same winner a full hits-ordered linear scan would, plus the newline fallback
that keeps that guarantee exact. The exact/regex split itself now lives in
`DatabaseMappingItem.literal` (see `tests/database/test_mapper.py`) rather
than a per-process cache, so there is nothing here to invalidate on mutation
— every resolve reads current DB state directly.
"""

from uuid import UUID, uuid4

import pytest
from decoy import Decoy
from sqlalchemy.orm import Session

from slidetap.database import DatabaseAttribute, DatabaseMapper, DatabaseMappingItem
from slidetap.model import StringAttribute
from slidetap.services import (
    AttributeService,
    DatabaseService,
    SchemaService,
    ValidationService,
)
from slidetap.services.mapper_service import MapperService


def _mapping_item(
    mapper_uid: UUID, expression: str, hits: int = 0
) -> DatabaseMappingItem:
    item = DatabaseMappingItem(
        mapper_uid, expression, StringAttribute(uid=uuid4(), schema_uid=uuid4())
    )
    item.hits = hits
    return item


@pytest.fixture()
def attribute_service(decoy: Decoy) -> AttributeService:
    return decoy.mock(cls=AttributeService)


@pytest.fixture()
def validation_service(decoy: Decoy) -> ValidationService:
    return decoy.mock(cls=ValidationService)


@pytest.fixture()
def schema_service(decoy: Decoy) -> SchemaService:
    return decoy.mock(cls=SchemaService)


@pytest.fixture()
def database_service(decoy: Decoy) -> DatabaseService:
    return decoy.mock(cls=DatabaseService)


@pytest.fixture()
def mapper_service(
    attribute_service: AttributeService,
    validation_service: ValidationService,
    schema_service: SchemaService,
    database_service: DatabaseService,
) -> MapperService:
    return MapperService(
        attribute_service=attribute_service,
        validation_service=validation_service,
        schema_service=schema_service,
        database_service=database_service,
    )


@pytest.mark.unittest
class TestResolveExpression:
    def test_exact_candidate_wins_with_no_regex_overlap(
        self,
        decoy: Decoy,
        mapper_service: MapperService,
        database_service: DatabaseService,
    ):
        session = decoy.mock(cls=Session)
        mapper_uid = uuid4()
        decoy.when(
            database_service.get_exact_mapping_candidate(session, mapper_uid, "A")
        ).then_return(_mapping_item(mapper_uid, "^A$"))
        decoy.when(
            database_service.get_regex_mapping_items(session, mapper_uid)
        ).then_return([])

        assert mapper_service._resolve_expression(session, mapper_uid, "A") == "^A$"

    def test_no_candidates_returns_none(
        self,
        decoy: Decoy,
        mapper_service: MapperService,
        database_service: DatabaseService,
    ):
        session = decoy.mock(cls=Session)
        mapper_uid = uuid4()
        decoy.when(
            database_service.get_exact_mapping_candidate(
                session, mapper_uid, "does-not-exist"
            )
        ).then_return(None)
        decoy.when(
            database_service.get_regex_mapping_items(session, mapper_uid)
        ).then_return([_mapping_item(mapper_uid, ".*resectie.*")])

        assert (
            mapper_service._resolve_expression(session, mapper_uid, "does-not-exist")
            is None
        )

    def test_regex_only_match(
        self,
        decoy: Decoy,
        mapper_service: MapperService,
        database_service: DatabaseService,
    ):
        session = decoy.mock(cls=Session)
        mapper_uid = uuid4()
        decoy.when(
            database_service.get_exact_mapping_candidate(session, mapper_uid, "male")
        ).then_return(None)
        decoy.when(
            database_service.get_regex_mapping_items(session, mapper_uid)
        ).then_return(
            [
                _mapping_item(mapper_uid, ".*male.*"),
                _mapping_item(mapper_uid, ".*bovine.*"),
            ]
        )

        assert (
            mapper_service._resolve_expression(session, mapper_uid, "male")
            == ".*male.*"
        )

    def test_non_matching_regex_candidates_are_ignored(
        self,
        decoy: Decoy,
        mapper_service: MapperService,
        database_service: DatabaseService,
    ):
        # `get_regex_mapping_items` returns every regex-shaped expression for
        # the mapper; the resolver still has to re.match each one itself.
        session = decoy.mock(cls=Session)
        mapper_uid = uuid4()
        decoy.when(
            database_service.get_exact_mapping_candidate(session, mapper_uid, "7185")
        ).then_return(_mapping_item(mapper_uid, "^7185$"))
        decoy.when(
            database_service.get_regex_mapping_items(session, mapper_uid)
        ).then_return([_mapping_item(mapper_uid, ".*zzz.*")])

        assert (
            mapper_service._resolve_expression(session, mapper_uid, "7185") == "^7185$"
        )

    def test_higher_hits_regex_beats_lower_hits_exact(
        self,
        decoy: Decoy,
        mapper_service: MapperService,
        database_service: DatabaseService,
    ):
        """Winner is picked by (hits desc, uid) across exact and regex
        candidates together — the same ordering a full linear scan would use —
        so a heavily-hit regex key can still beat a fresh exact key."""
        session = decoy.mock(cls=Session)
        mapper_uid = uuid4()
        decoy.when(
            database_service.get_exact_mapping_candidate(
                session, mapper_uid, "71854001"
            )
        ).then_return(_mapping_item(mapper_uid, "^71854001$", hits=1))
        decoy.when(
            database_service.get_regex_mapping_items(session, mapper_uid)
        ).then_return([_mapping_item(mapper_uid, ".*854.*", hits=100)])

        assert (
            mapper_service._resolve_expression(session, mapper_uid, "71854001")
            == ".*854.*"
        )

    def test_tie_break_by_uid(
        self,
        decoy: Decoy,
        mapper_service: MapperService,
        database_service: DatabaseService,
    ):
        session = decoy.mock(cls=Session)
        mapper_uid = uuid4()
        exact = _mapping_item(mapper_uid, "^71854001$", hits=5)
        regex = _mapping_item(mapper_uid, ".*854.*", hits=5)
        # Force a deterministic uid ordering regardless of generation order.
        exact.uid, regex.uid = sorted([exact.uid, regex.uid])
        decoy.when(
            database_service.get_exact_mapping_candidate(
                session, mapper_uid, "71854001"
            )
        ).then_return(exact)
        decoy.when(
            database_service.get_regex_mapping_items(session, mapper_uid)
        ).then_return([regex])

        assert (
            mapper_service._resolve_expression(session, mapper_uid, "71854001")
            == exact.expression
        )

    def test_trailing_newline_value_uses_linear_scan(
        self,
        decoy: Decoy,
        mapper_service: MapperService,
        database_service: DatabaseService,
    ):
        """`^X$` matches `"X\\n"` under re.match (`$` matches before a trailing
        newline), which the exact string-equality lookup on `literal` would
        miss. A newline-bearing value is routed through the authoritative
        linear scan instead, independent of the exact/regex queries."""
        session = decoy.mock(cls=Session)
        mapper_uid = uuid4()
        decoy.when(
            database_service.get_mapper_expressions(session, mapper_uid)
        ).then_return(["^71854001$"])

        assert (
            mapper_service._resolve_expression(session, mapper_uid, "71854001\n")
            == "^71854001$"
        )


@pytest.mark.unittest
class TestGetMatchingExpressionSingle:
    def test_single_expression_branch_matches(
        self, decoy: Decoy, mapper_service: MapperService
    ):
        session = decoy.mock(cls=Session)
        mapper = decoy.mock(cls=DatabaseMapper)
        attribute = decoy.mock(cls=DatabaseAttribute)
        decoy.when(attribute.mappable_value).then_return("HE")

        assert (
            mapper_service._get_matching_expression(session, mapper, attribute, "^HE$")
            == "^HE$"
        )
        assert (
            mapper_service._get_matching_expression(session, mapper, attribute, "^XX$")
            is None
        )

    def test_none_value_returns_none(self, decoy: Decoy, mapper_service: MapperService):
        session = decoy.mock(cls=Session)
        mapper = decoy.mock(cls=DatabaseMapper)
        attribute = decoy.mock(cls=DatabaseAttribute)
        decoy.when(attribute.mappable_value).then_return(None)

        assert (
            mapper_service._get_matching_expression(session, mapper, attribute, None)
            is None
        )
