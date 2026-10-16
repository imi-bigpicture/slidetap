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

import pytest

from slidetap.services import MapperService
from slidetap.services.mapper_service import MAX_MAPPING_EXPRESSION_LENGTH


@pytest.mark.unittest
class TestMappingExpressionValidation:
    @pytest.mark.parametrize(
        "expression",
        [
            "HE",
            "Hematoxylin.*",
            r"^\d{4}-\d{2}$",
            r"(ab|cd)+",
            r"(\d+)?",
            r"(\w+) (\w+)",
            "x" * MAX_MAPPING_EXPRESSION_LENGTH,
        ],
    )
    def test_an_expression_that_can_be_matched_safely_is_accepted(
        self, expression: str
    ):
        MapperService.validate_expression(expression)

    def test_an_expression_that_does_not_compile_is_refused_with_why(self):
        with pytest.raises(ValueError, match="not a valid regular expression"):
            MapperService.validate_expression("(unclosed")

    def test_an_expression_that_is_too_long_is_refused(self):
        with pytest.raises(ValueError, match="at most"):
            MapperService.validate_expression("x" * (MAX_MAPPING_EXPRESSION_LENGTH + 1))

    @pytest.mark.parametrize(
        "expression", [r"(a+)+$", r"(a*)*", r"(.*)+x", r"(\w+\s?)*$", r"(a+){2,}"]
    )
    def test_an_expression_that_repeats_a_repetition_is_refused(self, expression: str):
        with pytest.raises(ValueError, match="exponential"):
            MapperService.validate_expression(expression)
