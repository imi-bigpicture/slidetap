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

from pathlib import Path

import pytest
from decoy import Decoy
from slidetap_example.config import ExampleConfig
from slidetap_example.interfaces.image_import import ExampleImageImportInterface

from slidetap.model import Image, Project


def _image(decoy: Decoy, identifier: str) -> Image:
    image = decoy.mock(cls=Image)
    decoy.when(image.identifier).then_return(identifier)
    decoy.when(image.name).then_return(identifier)
    return image


@pytest.fixture()
def test_data(tmp_path: Path) -> Path:
    test_data = tmp_path.joinpath("test_data")
    test_data.mkdir()
    return test_data


@pytest.fixture()
def image_import(test_data: Path) -> ExampleImageImportInterface:
    return ExampleImageImportInterface(
        ExampleConfig(
            example_test_data_path=test_data,
            example_test_data_image_extension=".svs",
        )
    )


@pytest.mark.unittest
class TestExampleImageImport:
    def test_an_identifier_with_a_dot_keeps_all_of_its_name(
        self,
        decoy: Decoy,
        image_import: ExampleImageImportInterface,
        test_data: Path,
    ):
        # Arrange
        image_folder = test_data.joinpath("A.1")
        image_folder.mkdir()
        image_folder.joinpath("A.1.svs").touch()

        # Act
        folder, files = image_import.download(
            _image(decoy, "A.1"), decoy.mock(cls=Project)
        )

        # Assert
        assert folder == image_folder
        assert list(files) == [image_folder.joinpath("A.1.svs")]

    @pytest.mark.parametrize("identifier", ["..", "../outside", "nested/name", "", "."])
    def test_an_identifier_that_is_not_a_folder_name_is_refused(
        self,
        decoy: Decoy,
        image_import: ExampleImageImportInterface,
        identifier: str,
    ):
        with pytest.raises(ValueError, match="not a folder name"):
            image_import.download(_image(decoy, identifier), decoy.mock(cls=Project))

    def test_an_absolute_identifier_is_refused(
        self,
        decoy: Decoy,
        image_import: ExampleImageImportInterface,
        tmp_path: Path,
    ):
        with pytest.raises(ValueError, match="not a folder name"):
            image_import.download(
                _image(decoy, str(tmp_path.joinpath("outside"))),
                decoy.mock(cls=Project),
            )
