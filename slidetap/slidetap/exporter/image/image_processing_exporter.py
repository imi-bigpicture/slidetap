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

from typing import Optional

from flask import Flask

from slidetap.database.project import Image, Project
from slidetap.exporter.image.image_exporter import ImageExporter
from slidetap.image_processing.step_image_processor import ImagePostProcessor
from slidetap.scheduler import Scheduler
from slidetap.storage.storage import Storage


class ImageProcessingExporter(ImageExporter):
    def __init__(
        self,
        scheduler: Scheduler,
        post_processor: ImagePostProcessor,
        storage: Storage,
        app: Optional[Flask] = None,
    ):
        self._post_processor = post_processor
        super().__init__(scheduler, storage, app)

    def init_app(self, app: Flask):
        super().init_app(app)
        self._post_processor.init_app(app)

    @property
    def processor(self) -> ImagePostProcessor:
        return self._post_processor

    def export(self, project: Project):
        """Should export the image to storage."""
        project.set_as_post_processing()
        images = Image.get_for_project(project.uid)
        for image in images:
            self._scheduler.add_job(
                str(image.uid),
                self.processor.run,
                {"image_uid": image.uid},
            )
