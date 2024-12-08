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
from pytest_unordered import unordered
from slidetap.database import DatabaseProject, DatabaseSample, DatabaseSampleSchema
from tests.conftest import create_sample


@pytest.mark.unittest
class TestSlideTapDatabaseSample:
    def test_get_or_add_child_slide_already_added(
        self, project: DatabaseProject, sample: DatabaseSample, slide: DatabaseSample
    ):
        # Arrange
        sample_schema = DatabaseSampleSchema.get_or_create(
            project.root_schema, "Slide", "Slide", 0
        )

        # Act
        existing_slide = DatabaseSample.get_or_add_child(
            "slide 1", sample_schema, [sample]
        )

        # Assert
        assert existing_slide == slide
        assert sample.children == [slide]
        assert slide.parents == [sample]

    def test_get_or_add_child_new_slide_to_sample(
        self, project: DatabaseProject, sample: DatabaseSample, slide: DatabaseSample
    ):
        # Arrange
        sample_schema = DatabaseSampleSchema.get_or_create(
            project.root_schema, "Slide", "Slide", 0
        )

        # Act
        new_slide = DatabaseSample.get_or_add_child("slide 2", sample_schema, [sample])

        # Assert
        assert new_slide != slide
        assert [slide, new_slide] == unordered(sample.children, check_type=False)
        assert new_slide.parents == [sample]

    def test_get_or_add_image_new_image_to_other_sample(
        self, project: DatabaseProject, sample: DatabaseSample, slide: DatabaseSample
    ):
        # Arrange
        sample_schema = DatabaseSampleSchema.get_or_create(
            project.root_schema, "Slide", "Slide", 0
        )
        other_sample = create_sample(project, "case 2")

        # Act
        new_slide = DatabaseSample.get_or_add_child(
            "slide 2", sample_schema, [other_sample]
        )

        # Assert
        assert new_slide != slide
        assert sample.children == [slide]
        assert slide.parents == [sample]
        assert other_sample.children == [new_slide]
        assert new_slide.parents == [other_sample]
