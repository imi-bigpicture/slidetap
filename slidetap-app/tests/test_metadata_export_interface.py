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

from uuid import uuid4

import pytest

from slidetap.external_interfaces import MetadataExportInterface
from slidetap.model import Dataset, ExportPreviewFile, Item, Project, Sample


class PreviewingExport(MetadataExportInterface):
    """Previews items alone, as an export that does not say what an item is
    connected to does."""

    def __init__(self, preview: str | None):
        self._preview = preview

    def preview_item(self, item: Item) -> str | None:
        return self._preview

    def export(self, project: Project, dataset: Dataset) -> None:
        pass


@pytest.mark.unittest
class TestMetadataExportInterface:
    def test_the_export_preview_is_the_item_alone_by_default(self):
        # Arrange
        item = Sample(
            uid=uuid4(),
            identifier="case 1",
            dataset_uid=uuid4(),
            schema_uid=uuid4(),
            batch_uid=uuid4(),
        )
        export = PreviewingExport("<case/>")

        # Act
        files = export.preview_export(item)

        # Assert
        assert files == [ExportPreviewFile(name="case 1", content="<case/>")]

    def test_nothing_previewed_is_no_files(self):
        # Arrange
        item = Sample(
            uid=uuid4(),
            identifier="case 1",
            dataset_uid=uuid4(),
            schema_uid=uuid4(),
            batch_uid=uuid4(),
        )
        export = PreviewingExport(None)

        # Act
        files = export.preview_export(item)

        # Assert
        assert files == []
