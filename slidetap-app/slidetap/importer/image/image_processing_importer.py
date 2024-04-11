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

from slidetap.image_processing import ImagePreProcessor
from slidetap.image_processing.image_processor import ImageProcessor
from slidetap.importer.image.image_importer import ImageImporter
from slidetap.scheduler import Scheduler


class ImageProcessingImporter(ImageImporter):

    def __init__(
        self,
        scheduler: Scheduler,
        pre_processor: ImagePreProcessor,
        app: Optional[Flask] = None,
    ):
        super().__init__(scheduler, app)
        self._pre_processor = pre_processor

    def init_app(self, app: Flask):
        super().init_app(app)
        self._pre_processor.init_app(app)

    @property
    def processor(self) -> ImageProcessor:
        return self._pre_processor
