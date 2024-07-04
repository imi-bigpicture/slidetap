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

from typing import Optional

from flask import Flask

from slidetap.database import Image, Project
from slidetap.exporter.exporter import Exporter
from slidetap.storage.storage import Storage
from slidetap.tasks import Scheduler


class ImageExporter(Exporter):
    def __init__(
        self,
        scheduler: Scheduler,
        storage: Storage,
        app: Optional[Flask] = None,
    ):
        super().__init__(scheduler, storage, app)

    def init_app(self, app: Flask):
        super().init_app(app)

    def export(self, project: Project):
        """Should export the image to storage."""
        project.set_as_post_processing()
        images = Image.get_for_project(project.uid)
        for image in images:
            self._post_process_image(image)

    def re_export(self, image: Image):
        """Should re-export the image to storage."""
        self._post_process_image(image)

    def _post_process_image(self, image: Image):
        self._scheduler.post_process_image(image)
