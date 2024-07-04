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
"""Global container with processors."""

from typing import Optional

from flask import Flask

from slidetap.flask_extension import FlaskExtension
from slidetap.tasks.processors.image import (
    ImagePostProcessor,
    ImagePreProcessor,
)
from slidetap.tasks.processors.metadata import (
    MetadataExportProcessor,
    MetadataImportProcessor,
)


class ProcessorContainer(FlaskExtension):

    def init_processors(
        self,
        image_pre_processor: Optional[ImagePreProcessor] = None,
        image_post_processor: Optional[ImagePostProcessor] = None,
        metadata_export_processor: Optional[MetadataExportProcessor] = None,
        metadata_import_processor: Optional[MetadataImportProcessor] = None,
    ):
        self._image_pre_processor = image_pre_processor
        self._image_post_processor = image_post_processor
        self._metadata_export_processor = metadata_export_processor
        self._metadata_import_processor = metadata_import_processor

    def init_app(self, app: Flask):
        if self._image_pre_processor is not None:
            self._image_pre_processor.init_app(app)
        if self._image_post_processor is not None:
            self._image_post_processor.init_app(app)
        if self._metadata_export_processor is not None:
            self._metadata_export_processor.init_app(app)
        if self._metadata_import_processor is not None:
            self._metadata_import_processor.init_app(app)
        return super().init_app(app)

    @property
    def image_pre_processor(self):
        if self._image_pre_processor is None:
            raise ValueError("Image pre-processor is not set.")
        return self._image_pre_processor

    @image_pre_processor.setter
    def image_pre_processor(self, value: ImagePreProcessor):
        self._image_pre_processor = value

    @property
    def image_post_processor(self):
        if self._image_post_processor is None:
            raise ValueError("Image post-processor is not set.")
        return self._image_post_processor

    @image_post_processor.setter
    def image_post_processor(self, value: ImagePostProcessor):
        self._image_post_processor = value

    @property
    def metadata_export_processor(self):
        if self._metadata_export_processor is None:
            raise ValueError("Metadata export processor is not set.")
        return self._metadata_export_processor

    @metadata_export_processor.setter
    def metadata_export_processor(self, value: MetadataExportProcessor):
        self._metadata_export_processor = value

    @property
    def metadata_import_processor(self):
        if self._metadata_import_processor is None:
            raise ValueError("Metadata import processor is not set.")
        return self._metadata_import_processor

    @metadata_import_processor.setter
    def metadata_import_processor(self, value: MetadataImportProcessor):
        self._metadata_import_processor = value


processor_container = ProcessorContainer()
