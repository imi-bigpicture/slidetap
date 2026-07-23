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

"""Tests for the shared literal/regex mapping-expression classifier."""

import pytest

from slidetap.util.mapper_matching import literal_key


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
        assert literal_key(expression) == expected

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
        assert literal_key(expression) is None
