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

from wsidicomizer.metadata import WsiDicomizerMetadata

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
        Storing to the outbox is handled separately when the batch is completed.

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
            The task ID, used to isolate processing output per task.

        Returns
        -------
        Image
            The exported image with ``folder_path`` and ``thumbnail_path``
            pointing to the task-specific processing directory.
        """
        raise NotImplementedError()

    def create_export_metadata(
        self, image: Image, base: WsiDicomizerMetadata
    ) -> WsiDicomizerMetadata | None:
        """The metadata that belongs in the exported files of an image.

        Asked for again when the images are written to the outbox, which is
        after everything has been curated: what was written into the files at
        export was read from items that may have been edited since, and only
        the application knows what it read.

        base is what the image file said about itself before it was converted,
        for the same reason it is given to DicomMetadataProducer.create: what
        the application writes is written over it, and every field it models is
        set here, empty ones included.

        None where the export format carries no metadata of its own, which is
        also what an implementation that has not thought about it says: the
        files are then moved across as they are.
        """
        return None
