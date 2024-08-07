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
from flask import current_app
from pytest_unordered import unordered
from slidetap.database.project import Image, Project, Sample
from slidetap.database.schema.item_schema import ImageSchema
from slidetap.model.image_status import ImageStatus
from slidetap.model.project_status import ProjectStatus
from tests.conftest import create_image, create_sample


@pytest.mark.unittest
class TestSlideTapDatabaseImage:
    def test_get_or_add_image_already_added(
        self, project: Project, sample: Sample, image: Image
    ):
        # Arrange
        image_schema = ImageSchema.get_or_create(project.root_schema, "WSI", "wsi", 0)

        # Act
        existing_image = Image.get_or_add(image.identifier, image_schema, [sample])

        # Assert
        assert existing_image == image
        assert sample.images == [image]
        assert image.samples == [sample]

    def test_get_or_add_new_image_to_sample(
        self, project: Project, sample: Sample, image: Image
    ):
        # Arrange
        image_schema = ImageSchema.get_or_create(project.root_schema, "WSI", "wsi", 0)

        # Act
        new_image = Image.get_or_add("image 2", image_schema, [sample])

        # Assert
        assert new_image != image
        assert [image, new_image] == unordered(sample.images, check_type=False)
        assert new_image.samples == [sample]

    def test_get_or_add_new_image_to_other_sample(
        self, project: Project, sample: Sample, image: Image
    ):
        # Arrange
        image_schema = ImageSchema.get_or_create(project.root_schema, "WSI", "wsi", 0)
        other_sample = create_sample(project, "case 2")

        # Act
        new_image = Image.get_or_add("image 2", image_schema, [other_sample])

        # Assert
        assert new_image != image
        assert sample.images == [image]
        assert image.samples == [sample]
        assert other_sample.images == [new_image]
        assert new_image.samples == [other_sample]

    @pytest.mark.parametrize(
        "set_value, sample_value",
        [(True, False), (True, False), (False, False), (False, False)],
    )
    def test_select(
        self, sample: Sample, image: Image, set_value: bool, sample_value: bool
    ):
        # Arrange
        sample.selected = sample_value

        # Act
        image.select(set_value)

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
        project: Project,
        set_value: bool,
        initial_value: bool,
        sample_values: Tuple[bool, bool],
        expected_result: bool,
    ):
        # Arrange
        sample_1 = create_sample(project, "case 1")
        sample_2 = create_sample(project, "case 2")
        image = create_image(project, [sample_1, sample_2])
        sample_1.selected = sample_values[0]
        sample_2.selected = sample_values[1]
        image.selected = initial_value

        # Act
        image.select_from_sample(set_value)

        # Assert
        assert image.selected == expected_result

    def test_get_images_with_thumbnails(self, project: Project, sample: Sample):
        # Arrange
        image_1 = create_image(project, [sample], "image 1")
        image_2 = create_image(project, [sample], "image 2")
        image_1.thumbnail_path = "path to thumbnail"

        # Act
        images_with_thumbnails = Image.get_images_with_thumbnails(project)

        # Assert
        assert image_1 in images_with_thumbnails
        assert image_2 not in images_with_thumbnails

    @pytest.mark.parametrize(
        "project_status, image_statuses, expected_project_status, ",
        [
            (
                ProjectStatus.FAILED,
                (ImageStatus.POST_PROCESSED, ImageStatus.POST_PROCESSED),
                ProjectStatus.FAILED,
            ),
            (
                ProjectStatus.IMAGE_POST_PROCESSING,
                (ImageStatus.POST_PROCESSING, ImageStatus.POST_PROCESSED),
                ProjectStatus.IMAGE_POST_PROCESSING,
            ),
            (
                ProjectStatus.IMAGE_POST_PROCESSING,
                (ImageStatus.POST_PROCESSING_FAILED, ImageStatus.POST_PROCESSED),
                ProjectStatus.IMAGE_POST_PROCESSING_COMPLETE,
            ),
            (
                ProjectStatus.IMAGE_POST_PROCESSING,
                (ImageStatus.POST_PROCESSED, ImageStatus.POST_PROCESSED),
                ProjectStatus.IMAGE_POST_PROCESSING_COMPLETE,
            ),
        ],
    )
    def test_status_if_finished(
        self,
        project: Project,
        sample: Sample,
        project_status: ProjectStatus,
        image_statuses: Tuple[ImageStatus, ImageStatus],
        expected_project_status: ProjectStatus,
    ):
        # Arrange
        project.status = project_status
        image_1 = create_image(project, [sample], "image 1")
        image_2 = create_image(project, [sample], "image 2")
        image_1.status = image_statuses[0]
        image_2.status = image_statuses[1]

        # Act
        image_1.project.set_status_if_all_images_post_processed()

        # Assert
        assert project.status == expected_project_status
