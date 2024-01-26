import pytest
from pytest_unordered import unordered
from tests.conftest import create_sample

from slidetap.database.project import Project, Sample
from slidetap.database.schema.item_schema import SampleSchema


@pytest.mark.unittest
class TestSlideTapDatabaseSample:
    def test_get_or_add_child_slide_already_added(
        self, project: Project, sample: Sample, slide: Sample
    ):
        # Arrange
        sample_schema = SampleSchema.get_or_create(
            project.root_schema, "Slide", "Slide", 0
        )

        # Act
        existing_slide = Sample.get_or_add_child("slide 1", sample_schema, [sample])

        # Assert
        assert existing_slide == slide
        assert sample.children == [slide]
        assert slide.parents == [sample]

    def test_get_or_add_child_new_slide_to_sample(
        self, project: Project, sample: Sample, slide: Sample
    ):
        # Arrange
        sample_schema = SampleSchema.get_or_create(
            project.root_schema, "Slide", "Slide", 0
        )

        # Act
        new_slide = Sample.get_or_add_child("slide 2", sample_schema, [sample])

        # Assert
        assert new_slide != slide
        assert [slide, new_slide] == unordered(sample.children, check_type=False)
        assert new_slide.parents == [sample]

    def test_get_or_add_image_new_image_to_other_sample(
        self, project: Project, sample: Sample, slide: Sample
    ):
        # Arrange
        sample_schema = SampleSchema.get_or_create(
            project.root_schema, "Slide", "Slide", 0
        )
        other_sample = create_sample(project, "case 2")

        # Act
        new_slide = Sample.get_or_add_child("slide 2", sample_schema, [other_sample])

        # Assert
        assert new_slide != slide
        assert sample.children == [slide]
        assert slide.parents == [sample]
        assert other_sample.children == [new_slide]
        assert new_slide.parents == [other_sample]
