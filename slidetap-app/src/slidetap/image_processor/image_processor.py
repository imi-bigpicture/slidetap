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
from pathlib import Path
from typing import Sequence

from slidetap.image_processor.image_processing_step import (
    ImageProcessingStep,
)
from slidetap.model import Image
from slidetap.model.batch import Batch
from slidetap.model.project import Project
from slidetap.services import SchemaService, StorageService


class ImageProcessor:
    """Image processor that runs a sequence of steps on the processing image."""

    def __init__(
        self,
        storage_service: StorageService,
        schema_service: SchemaService,
        steps: Sequence[ImageProcessingStep],
    ):
        """Create a StepImageProcessor.

        Parameters
        ----------
        storage: Storage
        steps: Iterable[ImageProcessingStepsType]
        """
        self._steps = steps
        self._storage_service = storage_service
        self._root_schema = schema_service.root

    def run(self, image: Image, batch: Batch, project: Project) -> Image:
        logging.debug(f"Processing image {image.uid}.")
        if image.folder_path is None:
            raise FileNotFoundError(f"Image {image.uid} does not have a folder path. ")
        processing_path = Path(image.folder_path)
        try:
            for step in self._steps:
                try:
                    processing_path, image = step.run(
                        self._root_schema,
                        self._storage_service,
                        project,
                        image,
                        processing_path,
                    )
                except Exception as exception:
                    raise Exception(
                        f"Processing failed for {image.uid} name {image.name} "
                        f"at step {step}."
                    ) from exception

            logging.debug(f"Processing complete for {image.uid}.")
            image.folder_path = str(processing_path)
            return image
        finally:
            logging.debug(f"Cleanup {image.uid} name {image.name}.")
            for step in self._steps:
                step.cleanup(project, image)
