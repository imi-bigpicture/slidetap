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

"""Metaclass for metadata exporter."""

from abc import ABCMeta, abstractmethod

from flask import current_app

from slidetap.exporter.exporter import Exporter
from slidetap.model.item import Item
from slidetap.model.project import Project


class MetadataExporter(Exporter, metaclass=ABCMeta):
    """Metaclass for metadata exporter."""

    @abstractmethod
    def export(self, project: Project):
        raise NotImplementedError()

    @abstractmethod
    def preview_item(self, item: Item) -> str:
        """Should return a preview of the item."""
        raise NotImplementedError()


class BackgroundMetadataExporter(MetadataExporter):
    def export(self, project: Project):
        current_app.logger.info(f"Exporting project {project}.")
        self._project_service.set_as_exporting(project)
        self._scheduler.metadata_project_export(project)
