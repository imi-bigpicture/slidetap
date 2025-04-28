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


import json
from pathlib import Path
from typing import Any, Dict, Iterable

from slidetap.apps.example.metadata_serializer import JsonMetadataSerializer
from slidetap.model.item import Item
from slidetap.model.project import Project
from slidetap.service_provider import ServiceProvider
from slidetap.task.processors.dataset.dataset_import_processor import (
    DatasetImportProcessor,
)


class ExampleDatasetImportProcessor(DatasetImportProcessor):
    def __init__(self, service_provider: ServiceProvider):
        self._database_service = service_provider.database_service
        self._serializer = JsonMetadataSerializer()

    def run(self, path: Path, **kwargs: Dict[str, Any]):
        metadata_folder = "metadata"
        with self._database_service.get_session() as session:
            self._load_project(path / metadata_folder / "project.json")
            self._load_specimens(path / metadata_folder / "specimen.json")
            self._load_blocks(path / metadata_folder / "block.json")
            self._load_slides(path / metadata_folder / "slide.json")
            self._load_images(path / metadata_folder / "wsi.json")

    def _load_project(self, project_file: Path) -> Project:
        with project_file.open("r") as file:
            data = json.load(file)
        project = self._serializer.deserialize_project(data)
        return project

    def _load_specimens(self, specimens_file: Path) -> Iterable[Item]:
        with specimens_file.open("r") as file:
            data = json.load(file)
        return self._serializer.deserialize_items(data)

    def _load_blocks(self, blocks_file: Path) -> Iterable[Item]:
        with blocks_file.open("r") as file:
            data = json.load(file)
        return self._serializer.deserialize_items(data)

    def _load_slides(self, slides_file: Path) -> Iterable[Item]:
        with slides_file.open("r") as file:
            data = json.load(file)
        return self._serializer.deserialize_items(data)

    def _load_images(self, images_file: Path) -> Iterable[Item]:
        with images_file.open("r") as file:
            data = json.load(file)
        return self._serializer.deserialize_items(data)
