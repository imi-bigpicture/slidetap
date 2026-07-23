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

"""Tests for DatabaseMappingItem.literal (Nexus #46 follow-up).

`literal` is set from `expression` at both write points (`__init__` and
`update`) using the shared `literal_key` classifier, so it never drifts out
of sync with `expression`. The resolver (see `MapperService._resolve_expression`
and `DatabaseService.get_exact_mapping_candidate`) depends on that invariant.
"""

from uuid import uuid4

import pytest

from slidetap.database import DatabaseMappingItem
from slidetap.model import Code, CodeAttribute


def _attribute() -> CodeAttribute:
    return CodeAttribute(
        uid=uuid4(),
        schema_uid=uuid4(),
        original_value=Code(code="code", scheme="scheme", meaning="meaning"),
    )


@pytest.mark.unittest
class TestDatabaseMappingItemLiteral:
    def test_init_sets_literal_for_a_plain_literal_expression(self):
        item = DatabaseMappingItem(uuid4(), "^71854001$", _attribute())
        assert item.literal == "71854001"

    def test_init_leaves_literal_none_for_a_regex_expression(self):
        item = DatabaseMappingItem(uuid4(), ".*resectie.*", _attribute())
        assert item.literal is None

    def test_update_recomputes_literal_from_the_new_expression(self):
        item = DatabaseMappingItem(uuid4(), "^71854001$", _attribute())

        item.update(".*resectie.*", _attribute())
        assert item.literal is None

        item.update("^Female$", _attribute())
        assert item.literal == "Female"
