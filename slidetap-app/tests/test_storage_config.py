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

from pathlib import Path

import pytest

from slidetap.config import ConfigParser, StorageConfig


@pytest.mark.unittest
class TestStorageConfig:
    def test_all_folders_are_under_storage_by_default(self):
        # Arrange
        parser = ConfigParser(config={}, env={"SLIDETAP_STORAGE": "/share"})

        # Act
        config = StorageConfig.parse(parser)

        # Assert
        assert config.outbox == Path("/share/storage")
        assert config.download == Path("/share/download")
        assert config.processing == Path("/share/processing")

    def test_download_and_processing_can_be_set_apart_from_storage(self):
        # Arrange
        parser = ConfigParser(
            config={},
            env={
                "SLIDETAP_STORAGE": "/share",
                "SLIDETAP_DOWNLOAD": "/local/download",
                "SLIDETAP_PROCESSING": "/local/processing",
            },
        )

        # Act
        config = StorageConfig.parse(parser)

        # Assert
        assert config.outbox == Path("/share/storage")
        assert config.download == Path("/local/download")
        assert config.processing == Path("/local/processing")

    def test_empty_value_falls_back_to_storage(self):
        # Arrange
        parser = ConfigParser(
            config={},
            env={"SLIDETAP_STORAGE": "/share", "SLIDETAP_DOWNLOAD": ""},
        )

        # Act
        config = StorageConfig.parse(parser)

        # Assert
        assert config.download == Path("/share/download")
