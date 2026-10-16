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

"""Tests for DatabaseMappingItem.literal and DatabaseMappingItem.literal_key
(Nexus #46 follow-up).

`literal` is set from `expression` at both write points (`__init__` and
`update`) using `DatabaseMappingItem.literal_key`, so it never drifts out of
sync with `expression`. The resolver (see `MapperService._resolve_expression`
and `DatabaseService.get_literal_mapping_candidate`) depends on that
invariant.
"""

import importlib
from uuid import UUID, uuid4

import pytest

from slidetap.database import DatabaseMappingItem
from slidetap.model import CodeAttribute
from slidetap.services import DatabaseService

LITERAL_EXPRESSIONS = [
    ("^71854001$", "71854001"),  # canonical Diagnose key
    ("71854001$", "71854001"),  # start anchor is implicit under re.match
    ("^Female$", "Female"),
]

REGEX_EXPRESSIONS = [
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
]


@pytest.mark.unittest
class TestDatabaseMappingItemLiteral:
    def test_init_sets_literal_for_a_plain_literal_expression(
        self, code_attribute: CodeAttribute
    ):
        item = DatabaseMappingItem(uuid4(), "^71854001$", code_attribute)

        assert item.literal == "71854001"

    def test_init_leaves_literal_none_for_a_regex_expression(
        self, code_attribute: CodeAttribute
    ):
        item = DatabaseMappingItem(uuid4(), ".*resectie.*", code_attribute)

        assert item.literal is None

    def test_update_recomputes_literal_to_none_for_a_regex_expression(
        self, code_attribute: CodeAttribute
    ):
        item = DatabaseMappingItem(uuid4(), "^71854001$", code_attribute)

        item.update(".*resectie.*", code_attribute)

        assert item.literal is None

    def test_update_recomputes_literal_for_a_new_plain_literal_expression(
        self, code_attribute: CodeAttribute
    ):
        item = DatabaseMappingItem(uuid4(), "^71854001$", code_attribute)

        item.update("^Female$", code_attribute)

        assert item.literal == "Female"


@pytest.mark.unittest
class TestDatabaseMappingItemLiteralKey:
    @pytest.mark.parametrize(("expression", "expected"), LITERAL_EXPRESSIONS)
    def test_plain_literals_are_detected(self, expression: str, expected: str):
        assert DatabaseMappingItem.literal_key(expression) == expected

    @pytest.mark.parametrize("expression", REGEX_EXPRESSIONS)
    def test_regex_shaped_keys_are_rejected(self, expression: str):
        assert DatabaseMappingItem.literal_key(expression) is None


def _add_mapping_item(
    database_service: DatabaseService, mapper_uid: UUID, attribute: CodeAttribute
) -> UUID:
    with database_service.get_session() as session:
        mapping_item = DatabaseMappingItem(mapper_uid, "^code$", attribute)
        session.add(mapping_item)
        session.commit()
        return mapping_item.uid


def _hits(database_service: DatabaseService, mapping_item_uid: UUID) -> int:
    with database_service.get_session() as session:
        return session.get_one(DatabaseMappingItem, mapping_item_uid).hits


@pytest.mark.integration
class TestDatabaseMappingItemHits:
    def test_hits_counted_in_parallel_sessions_are_all_kept(
        self,
        sqlite_database_service: DatabaseService,
        mapper_uid: UUID,
        code_attribute: CodeAttribute,
    ):
        """The failure this guards against: two imports read the same count,
        each adds its hit to it, and the second to commit writes back a count
        that is missing the first one's hit."""
        # Arrange
        mapping_item_uid = _add_mapping_item(
            sqlite_database_service, mapper_uid, code_attribute
        )
        first_session = sqlite_database_service.create_session()()
        second_session = sqlite_database_service.create_session()()
        first_item = first_session.get_one(DatabaseMappingItem, mapping_item_uid)
        second_item = second_session.get_one(DatabaseMappingItem, mapping_item_uid)
        assert (first_item.hits, second_item.hits) == (0, 0)

        # Act
        first_item.increment_hits()
        first_session.commit()
        second_item.increment_hits()
        second_session.commit()
        first_session.close()
        second_session.close()

        # Assert
        assert _hits(sqlite_database_service, mapping_item_uid) == 2

    def test_a_hit_is_seen_in_the_session_and_not_written_back_on_flush(
        self,
        sqlite_database_service: DatabaseService,
        mapper_uid: UUID,
        code_attribute: CodeAttribute,
    ):
        # Arrange
        mapping_item_uid = _add_mapping_item(
            sqlite_database_service, mapper_uid, code_attribute
        )

        # Act
        with sqlite_database_service.get_session() as session:
            mapping_item = session.get_one(DatabaseMappingItem, mapping_item_uid)
            mapping_item.increment_hits()
            mapping_item.increment_hits()
            hits_in_session = mapping_item.hits
            session.flush()

        # Assert
        assert hits_in_session == 2
        assert _hits(sqlite_database_service, mapping_item_uid) == 2

    def test_a_hit_on_an_item_not_yet_stored_is_inserted_with_it(
        self,
        sqlite_database_service: DatabaseService,
        mapper_uid: UUID,
        code_attribute: CodeAttribute,
    ):
        # Act
        with sqlite_database_service.get_session() as session:
            mapping_item = DatabaseMappingItem(mapper_uid, "^code$", code_attribute)
            session.add(mapping_item)
            mapping_item.increment_hits()
            mapping_item_uid = mapping_item.uid

        # Assert
        assert _hits(sqlite_database_service, mapping_item_uid) == 1


@pytest.mark.unittest
class TestMigrationLiteralKeyParity:
    """Migration 70048a43fda6 carries a frozen copy of `literal_key` so that
    replaying it on a fresh environment backfills what it did when written,
    regardless of later changes to the live classifier.

    That freeze is only safe while the two still agree: if `literal_key`
    changes without a new migration to re-backfill, existing deployments keep
    `literal` values the resolver no longer expects. This test fails when they
    diverge, so the divergence is a deliberate decision rather than a silent
    one.
    """

    @pytest.mark.parametrize(
        "expression",
        [expression for expression, _ in LITERAL_EXPRESSIONS] + REGEX_EXPRESSIONS,
    )
    def test_frozen_copy_matches_the_live_classifier(self, expression: str):
        migration = importlib.import_module(
            "slidetap.migrations.versions.70048a43fda6_add_mapping_item_literal_column"
        )

        assert migration._literal_key(expression) == DatabaseMappingItem.literal_key(
            expression
        )
