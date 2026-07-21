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

Covers the exact-match index that replaces the O(n) linear regex scan, and the
`MapperService` wiring around it: caching, invalidation on mutation, and the
ambiguity fallback that keeps first-hit-wins behaviour identical to the
pre-index resolver.
"""

import re
from re import Pattern
from uuid import uuid4

import pytest
from decoy import Decoy
from sqlalchemy.orm import Session

from slidetap.database import DatabaseAttribute, DatabaseMapper
from slidetap.services import (
    AttributeService,
    DatabaseService,
    SchemaService,
    ValidationService,
)
from slidetap.services.mapper_service import (
    MapperExpressionIndex,
    MapperService,
    _literal_key,
)


class CountingCompiler:
    """A pattern compiler that records how many times it is invoked.

    In the resolver the compiler is called once per regex key scanned, so the
    call count is a deterministic proxy for "how much of the mapper did we
    scan" — the thing the fast path is meant to shrink.
    """

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, pattern: str) -> Pattern:
        self.calls += 1
        return re.compile(pattern)


@pytest.mark.unittest
class TestLiteralKey:
    @pytest.mark.parametrize(
        ("expression", "expected"),
        [
            ("^71854001$", "71854001"),  # canonical Diagnose key
            ("71854001$", "71854001"),  # start anchor is implicit under re.match
            ("^Female$", "Female"),
        ],
    )
    def test_plain_literals_are_detected(self, expression: str, expected: str):
        assert _literal_key(expression) == expected

    @pytest.mark.parametrize(
        "expression",
        [
            "^71854001",  # no end anchor -> prefix match, not exact
            "71854001",  # no end anchor
            ".*resectie.*",
            "^HE[0-9]*",
            "^a.b$",  # '.' is a metacharacter
            "^$",  # matches empty string only; not a useful literal
            # re.escape escapes '-' (and space, '#', '&', '~'), so these stay on
            # the safe regex path rather than being treated as exact literals.
            "^HE-01$",
            "^SN Mamma 4$",
        ],
    )
    def test_regex_shaped_keys_are_rejected(self, expression: str):
        assert _literal_key(expression) is None


@pytest.mark.unittest
class TestMapperExpressionIndex:
    def test_exact_hit_skips_the_regex_scan(self):
        expressions = [f"^{i}$" for i in range(5000)] + [".*resectie.*", "^HE[0-9]*"]
        index = MapperExpressionIndex.build(expressions)
        compiler = CountingCompiler()

        match = index.resolve("2500", compiler)

        assert match.expression == "^2500$"
        assert match.ambiguous is False
        # Only the two regex keys are compiled, never the 5000 exact keys.
        assert compiler.calls == 2

    def test_unmatched_value_returns_none(self):
        index = MapperExpressionIndex.build(["^A$", "^B$", ".*resectie.*"])
        match = index.resolve("does-not-exist", re.compile)
        assert match.expression is None
        assert match.ambiguous is False

    def test_regex_only_single_match(self):
        index = MapperExpressionIndex.build([".*male.*", ".*bovine.*"])
        match = index.resolve("male", re.compile)
        assert match.expression == ".*male.*"
        assert match.ambiguous is False

    def test_exact_anchor_does_not_prefix_match(self):
        # ^7185$ must match only "7185", unlike a bare "7185" regex which
        # re.match would accept as a prefix of "71854".
        index = MapperExpressionIndex.build(["^7185$"])
        assert index.resolve("71854", re.compile).expression is None
        assert index.resolve("7185", re.compile).expression == "^7185$"

    def test_exact_and_regex_overlap_is_ambiguous(self):
        # "71854001" hits the exact key AND ".*854.*".
        index = MapperExpressionIndex.build(["^71854001$", ".*854.*"])
        match = index.resolve("71854001", re.compile)
        assert match.ambiguous is True
        assert match.expression is None

    def test_two_regex_overlap_is_ambiguous(self):
        index = MapperExpressionIndex.build([".*male.*", ".*female.*"])
        match = index.resolve("female", re.compile)
        assert match.ambiguous is True

    def test_colliding_literals_are_demoted_to_scan(self):
        # Two expressions collapse to the literal "A"; neither owns the exact
        # slot, so the value is reported ambiguous for the caller to resolve.
        index = MapperExpressionIndex.build(["^A$", "A$"])
        match = index.resolve("A", re.compile)
        assert match.ambiguous is True


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
    def test_index_is_cached_across_resolves(
        self,
        decoy: Decoy,
        mapper_service: MapperService,
        database_service: DatabaseService,
    ):
        session = decoy.mock(cls=Session)
        mapper_uid = uuid4()
        # Second query returns an empty list: if the index were rebuilt on the
        # second resolve, "B" would resolve to None instead of "^B$".
        decoy.when(
            database_service.get_mapper_expressions(session, mapper_uid)
        ).then_return(["^A$", "^B$"], [])

        assert mapper_service._resolve_expression(session, mapper_uid, "A") == "^A$"
        assert mapper_service._resolve_expression(session, mapper_uid, "B") == "^B$"

    def test_invalidation_forces_rebuild(
        self,
        decoy: Decoy,
        mapper_service: MapperService,
        database_service: DatabaseService,
    ):
        session = decoy.mock(cls=Session)
        mapper_uid = uuid4()
        decoy.when(
            database_service.get_mapper_expressions(session, mapper_uid)
        ).then_return(["^A$"], ["^A$", "^B$"])

        # First index has only "^A$"; after invalidation the rebuilt index sees
        # "^B$" too — the differing results prove the rebuild happened.
        assert mapper_service._resolve_expression(session, mapper_uid, "B") is None
        mapper_service._invalidate_expression_index(mapper_uid)
        assert mapper_service._resolve_expression(session, mapper_uid, "B") == "^B$"

    def test_ambiguous_value_uses_linear_scan_order(
        self,
        decoy: Decoy,
        mapper_service: MapperService,
        database_service: DatabaseService,
    ):
        """When a value matches both an exact and a regex key, the winner is the
        first expression in the live hits-ordered scan — not the exact key —
        preserving pre-index first-hit-wins behaviour."""
        session = decoy.mock(cls=Session)
        mapper_uid = uuid4()
        # Regex key listed first, exact key second.
        decoy.when(
            database_service.get_mapper_expressions(session, mapper_uid)
        ).then_return([".*854.*", "^71854001$"])

        # "71854001" matches both keys; returning the regex key (first in order)
        # rather than the exact key proves the ambiguity fallback ran the
        # authoritative ordered scan.
        assert (
            mapper_service._resolve_expression(session, mapper_uid, "71854001")
            == ".*854.*"
        )

    def test_trailing_newline_value_matches_exact_key_via_scan(
        self,
        decoy: Decoy,
        mapper_service: MapperService,
        database_service: DatabaseService,
    ):
        """`^X$` matches `"X\\n"` under the old re.match scan (``$`` matches
        before a trailing newline). The dict lookup would miss it, so a
        newline-bearing value is routed through the authoritative scan to keep
        the result identical to the pre-index resolver."""
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
