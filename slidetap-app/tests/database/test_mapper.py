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

from uuid import uuid4

import pytest

from slidetap.database import DatabaseMappingItem
from slidetap.model import CodeAttribute


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
    @pytest.mark.parametrize(
        ("expression", "expected"),
        [
            ("^71854001$", "71854001"),  # canonical Diagnose key
            ("71854001$", "71854001"),  # start anchor is implicit under re.match
            ("^Female$", "Female"),
        ],
    )
    def test_plain_literals_are_detected(self, expression: str, expected: str):
        assert DatabaseMappingItem.literal_key(expression) == expected

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
        assert DatabaseMappingItem.literal_key(expression) is None
