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

from typing import Optional, Sequence

from flask import Flask

from slidetap.exporter.image import ImageProcessingExporter
from slidetap.image_processing.image_processing_step import ImageProcessingStep
from slidetap.image_processing.step_image_processor import ImagePostProcessor
from slidetap.scheduler import Scheduler
from slidetap.storage import Storage


class StepImageProcessingExporter(ImageProcessingExporter):
    """Image exporter that"""

    def __init__(
        self,
        scheduler: Scheduler,
        storage: Storage,
        steps: Sequence[ImageProcessingStep],
        app: Optional[Flask] = None,
    ):
        processor = ImagePostProcessor(
            storage,
            steps,
        )
        super().__init__(scheduler, processor, storage, app)
