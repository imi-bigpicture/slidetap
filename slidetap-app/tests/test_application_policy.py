#    Copyright 2026 SECTRA AB
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

"""How the application behaves, as the interfaces of its plugin say."""

import pytest
from dishka import make_container

from slidetap.application_policy import ApplicationPolicy
from slidetap.external_interfaces import ImageImportInterface
from slidetap.service_provider import BaseProvider


@pytest.mark.unittest
class TestAsTheImageImportSays:
    @pytest.mark.parametrize("separately", [True, False])
    def test_images_are_pre_processed_separately_as_the_import_says(
        self, separately: bool
    ):
        # Arrange
        class Import(ImageImportInterface):
            @property
            def pre_processes_separately(self) -> bool:
                return separately

            def download(self, image, project):  # type: ignore[override]
                raise NotImplementedError()

        provider = BaseProvider(
            schema_interface=lambda: None,  # type: ignore[arg-type,return-value]
            metadata_import_interface=lambda: None,  # type: ignore[arg-type,return-value]
            metadata_export_interface=lambda: None,  # type: ignore[arg-type,return-value]
            image_import_interface=Import,
        )
        container = make_container(provider, skip_validation=True)

        # Act
        policy = container.get(ApplicationPolicy)

        # Assert
        assert policy.pre_processes_images_separately is separately

    def test_images_are_pre_processed_separately_by_default(self):
        # Arrange
        class Import(ImageImportInterface):
            def download(self, image, project):  # type: ignore[override]
                raise NotImplementedError()

        # Act & Assert
        assert Import().pre_processes_separately is True


@pytest.mark.unittest
class TestForTheClient:
    def test_the_client_reads_it_in_camel_case(self):
        # Arrange
        policy = ApplicationPolicy(pre_processes_images_separately=False)

        # Act
        dumped = policy.model_dump(by_alias=True)

        # Assert
        assert dumped == {"preProcessesImagesSeparately": False}
