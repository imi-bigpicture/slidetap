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

"""Tests for `Cardinality`, which replaced the min/max integer pairs on item
relations. The pairs had two spellings for "unbounded" and every validator
compared them by hand; the enum has one predicate that all of them share, so
it is worth pinning to its whole truth table rather than to the cases that
happen to be declared today."""

import uuid

import pytest

from slidetap.model import Cardinality, ImageToSampleRelation


@pytest.mark.unittest
class TestCardinality:
    @pytest.mark.parametrize(
        ("cardinality", "allowed"),
        [
            (Cardinality.ONE, [False, True, False, False]),
            (Cardinality.ZERO_OR_ONE, [True, True, False, False]),
            (Cardinality.ONE_OR_MORE, [False, True, True, True]),
            (Cardinality.ZERO_OR_MORE, [True, True, True, True]),
        ],
    )
    def test_allows_counts_zero_to_three(
        self, cardinality: Cardinality, allowed: list[bool]
    ):
        # Arrange
        counts = [0, 1, 2, 3]

        # Act
        results = [cardinality.allows(count) for count in counts]

        # Assert
        assert results == allowed

    @pytest.mark.parametrize(
        ("cardinality", "required", "multiple"),
        [
            (Cardinality.ONE, True, False),
            (Cardinality.ZERO_OR_ONE, False, False),
            (Cardinality.ONE_OR_MORE, True, True),
            (Cardinality.ZERO_OR_MORE, False, True),
        ],
    )
    def test_bounds_read_off_the_name(
        self, cardinality: Cardinality, required: bool, multiple: bool
    ):
        # Arrange

        # Act

        # Assert
        assert cardinality.required is required
        assert cardinality.multiple is multiple

    def test_the_four_values_are_the_whole_space(self):
        """Every combination of the two bounds is named exactly once, so there
        is no constraint that has to be spelled two ways or cannot be spelled
        at all."""
        # Arrange

        # Act
        bounds = {
            (cardinality.required, cardinality.multiple) for cardinality in Cardinality
        }

        # Assert
        assert bounds == {(True, True), (True, False), (False, True), (False, False)}


@pytest.mark.unittest
class TestOrphanRelation:
    """An orphan relation is where an import parks an image it could not match
    to a slide. It has to be declarable so the image is not dropped, and it has
    to count towards nothing, so the image stays invalid until it is moved."""

    @staticmethod
    def _relation(orphan: bool) -> ImageToSampleRelation:
        return ImageToSampleRelation(
            uid=uuid.uuid4(),
            name="image of sample",
            image_uid=uuid.uuid4(),
            sample_uid=uuid.uuid4(),
            image_title="Image",
            sample_title="Sample",
            orphan=orphan,
        )

    def test_relations_describe_the_data_unless_marked_otherwise(self):
        # Arrange

        # Act
        relation = self._relation(orphan=False)

        # Assert
        assert relation.orphan is False

    def test_an_orphan_relation_can_be_declared(self):
        # Arrange

        # Act
        relation = self._relation(orphan=True)

        # Assert
        assert relation.orphan is True
        # Its cardinality is still whatever it says; the validator skips the
        # relation rather than reading a different bound off it.
        assert relation.samples is Cardinality.ONE_OR_MORE
