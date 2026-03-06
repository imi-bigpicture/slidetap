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

from abc import ABCMeta, abstractmethod

from slidetap.model import Batch, Image, Project


class ImageExportInterface(metaclass=ABCMeta):
    """
    Metaclass for interface for exporting images. Implementations must implement:
    - export: Format an image to the export format and save it to storage.
    """

    @abstractmethod
    def export(
        self,
        image: Image,
        batch: Batch,
        project: Project,
        task_id: str,
    ) -> Image:
        """
        Export image file to the export format and save it to a task-specific
        processing directory.

        Output files must be written to the processing directory identified by
        ``task_id`` (via ``StorageService``), **not** directly to the outbox.
        The outbox publish is handled separately when the batch is completed.

        Must throw an exception if the image cannot be exported.

        Parameters
        ----------
        image: Image
            The image to export.
        batch: Batch
            The batch to which the image belongs.
        project: Project
            The project to which the image belongs.
        task_id: str
            The Celery task ID, used to isolate processing output per task.

        Returns
        -------
        Image
            The exported image with ``folder_path`` and ``thumbnail_path``
            pointing to the task-specific processing directory.
        """
        raise NotImplementedError()
