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

import logging
from typing import Optional
from uuid import UUID

from slidetap.external_interfaces import MetadataExportInterface
from slidetap.model import Project
from slidetap.services import ProjectService
from slidetap.services.database_service import DatabaseService
from slidetap.task import Scheduler


class MetadataExportService:
    def __init__(
        self,
        scheduler: Scheduler,
        project_service: ProjectService,
        database_service: DatabaseService,
        metadata_export_interface: MetadataExportInterface,
    ):
        self._scheduler = scheduler
        self._project_service = project_service
        self._database_service = database_service
        self._metadata_export_interface = metadata_export_interface

    def export(self, project: Project):
        logging.info(f"Exporting project {project}.")
        self._project_service.set_as_exporting(project)
        self._scheduler.metadata_project_export(project)

    def preview_item(self, item_uid: UUID) -> Optional[str]:
        """Should return a preview of the item."""
        with self._database_service.get_session() as session:
            item = self._database_service.get_item(session, item_uid)
            return self._metadata_export_interface.preview_item(item.model)
