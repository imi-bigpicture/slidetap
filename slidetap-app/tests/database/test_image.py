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

from typing import Tuple

import pytest
from pytest_unordered import unordered
from slidetap.database import (
    DatabaseImage,
    DatabaseProject,
    DatabaseSample,
)
from slidetap.model import (
    Image,
    ImageStatus,
    Project,
    ProjectStatus,
    RootSchema,
    Sample,
)
from tests.conftest import create_image, create_sample


@pytest.mark.unittest
class TestSlideTapDatabaseImage:
    @pytest.mark.parametrize(
        "set_value, sample_value",
        [(True, False), (True, False), (False, False), (False, False)],
    )
    def test_select(
        self,
        schema: RootSchema,
        sample: Sample,
        image: Image,
        set_value: bool,
        sample_value: bool,
    ):
        # Arrange
        database_sample = DatabaseSample.get_or_create_from_model(
            sample, schema.samples["case"]
        )
        database_sample.selected = sample_value
        database_image = DatabaseImage.get_or_create_from_model(
            image, schema.samples["wsi"]
        )

        # Act
        database_image.select(set_value)

        # Assert
        assert image.selected == set_value
        assert sample.selected == set_value

    @pytest.mark.parametrize(
        "set_value, initial_value, sample_values, expected_result",
        [
            (True, True, (True, True), True),
            (True, True, (True, False), True),
            (True, False, (True, False), False),
            (False, False, (True, False), False),
        ],
    )
    def test_select_from_sample(
        self,
        schema: RootSchema,
        project: Project,
        set_value: bool,
        initial_value: bool,
        sample_values: Tuple[bool, bool],
        expected_result: bool,
    ):
        # Arrange
        sample_1 = create_sample(schema, project, "case 1")
        sample_2 = create_sample(schema, project, "case 2")
        image = create_image(schema, project, [sample_1.uid, sample_2.uid])
        database_sample_1 = DatabaseSample.get_or_create_from_model(
            sample_1, schema.samples["case"]
        )
        database_sample_2 = DatabaseSample.get_or_create_from_model(
            sample_2, schema.samples["case"]
        )
        database_image = DatabaseImage.get_or_create_from_model(
            image, schema.samples["wsi"]
        )
        database_sample_1.selected = sample_values[0]
        database_sample_2.selected = sample_values[1]
        database_image.selected = initial_value

        # Act
        database_image.select_from_sample(set_value)

        # Assert
        assert image.selected == expected_result

    def test_get_images_with_thumbnails(
        self, project: DatabaseProject, sample: DatabaseSample
    ):
        # Arrange
        image_1 = create_image(project, [sample], "image 1")
        image_2 = create_image(project, [sample], "image 2")
        image_1.thumbnail_path = "path to thumbnail"

        # Act
        images_with_thumbnails = DatabaseImage.get_images_with_thumbnails(project)

        # Assert
        assert image_1 in images_with_thumbnails
        assert image_2 not in images_with_thumbnails
