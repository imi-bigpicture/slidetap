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

from typing import Any, Dict
from uuid import UUID

from slidetap.config import Config
from slidetap.external_interfaces import ImageExportInterface
from slidetap.image_processor.image_processing_step import (
    CreateThumbnails,
    DicomProcessingStep,
    FinishingStep,
    StoreProcessingStep,
)
from slidetap.image_processor.image_processor import ImagePostProcessor
from slidetap.service_provider import ServiceProvider


class ExampleImageExportInterface(ImageExportInterface):
    def __init__(self, service_provider: ServiceProvider, config: Config):
        self._service_provider = service_provider
        self._config = config

    def export(self, image_uid: UUID, **kwargs: Dict[str, Any]) -> None:
        processor = ImagePostProcessor(
            self._service_provider,
            [
                DicomProcessingStep(
                    config=self._config.dicomization_config,
                    use_pseudonyms=False,
                ),
                CreateThumbnails(use_pseudonyms=False),
                StoreProcessingStep(use_pseudonyms=False),
                FinishingStep(),
            ],
        )
        processor.run(image_uid)
