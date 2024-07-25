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

"""Module for handling background tasks."""

from slidetap.tasks.celery import SlideTapCeleryAppFactory
from slidetap.tasks.processors import (
    CreateThumbnails,
    DicomProcessingStep,
    FinishingStep,
    ImagePostProcessor,
    ImagePreProcessor,
    ImageProcessingStep,
    MetadataExportProcessor,
    MetadataImportProcessor,
    ProcessorFactory,
    StoreProcessingStep,
)
from slidetap.tasks.scheduler import (
    ApScheduler,
    CeleryScheduler,
    Queue,
    Scheduler,
)
