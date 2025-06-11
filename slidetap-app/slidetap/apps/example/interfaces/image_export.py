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


from slidetap.config import Config
from slidetap.external_interfaces import ImageExportInterface
from slidetap.image_processor import (
    CreateThumbnails,
    DicomProcessingStep,
    FinishingStep,
    ImageProcessor,
    StoreProcessingStep,
)
from slidetap.model import Batch, Image, Project
from slidetap.services import SchemaService, StorageService


class ExampleImageExportInterface(ImageExportInterface):
    def __init__(
        self,
        storage_service: StorageService,
        schema_service: SchemaService,
        config: Config,
    ):
        self._processor = ImageProcessor(
            storage_service,
            schema_service,
            [
                DicomProcessingStep(
                    config=config.dicomization_config,
                    use_pseudonyms=False,
                ),
                CreateThumbnails(use_pseudonyms=False),
                StoreProcessingStep(use_pseudonyms=False),
                FinishingStep(),
            ],
        )

    def export(self, image: Image, batch: Batch, project: Project) -> Image:
        return self._processor.run(image, batch, project)
