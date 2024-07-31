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

"""Image processing steps that run under a StepImageProcessor."""

import io
import os
from abc import ABCMeta, abstractmethod
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, Optional
from uuid import UUID

from flask import current_app
from opentile.config import settings as opentile_settings
from wsidicom import WsiDicom
from wsidicomizer import WsiDicomizer
from wsidicomizer.metadata import WsiDicomizerMetadata

from slidetap.config import DicomizationConfig
from slidetap.database import Image, ImageFile
from slidetap.storage import Storage
from slidetap.task.processors.processor import Processor


class ImageProcessingStep(Processor, metaclass=ABCMeta):
    """Metaclass for an image processing step.

    Steps should not commit changes to the database. This is done when all the steps
    have been completed, so that the changes can be rolled back if an error occurs."""

    @abstractmethod
    def run(self, storage: Storage, image: Image, path: Path) -> Path:
        """Should implement the action of the processing step.

        Parameters
        ----------
        image: Image
            The image that is being processed.
        path: Path
            The path to the image file to process.
        """
        raise NotImplementedError()

    def cleanup(self, image: Image):
        """Should implement any needed clean up to do after the processing
        step.

        Parameters
        ----------
        image: Image
            The image that should be cleaned up.
        """
        pass

    @contextmanager
    def _open_wsi(
        self,
        image: Image,
        path: Path,
        metadata: Optional[WsiDicomizerMetadata] = None,
        **kwargs,
    ):
        try:
            with self._open_wsidicom(image, path, **kwargs) as wsi:
                yield wsi
                return
        except Exception:
            pass
        try:
            opentile_settings.ndpi_frame_cache = 4
            with self._open_wsidicomizer(
                image, path, metadata=metadata, **kwargs
            ) as wsi:
                yield wsi
                return
        except Exception:
            yield None
            return

    @contextmanager
    def _open_wsidicomizer(
        self,
        image: Image,
        path: Path,
        metadata: Optional[WsiDicomizerMetadata] = None,
        **kwargs,
    ):
        if len(image.files) == 0:
            current_app.logger.error(f"No image files for image {image.identifier}")
            yield
        for file in image.files:
            image_path = path.joinpath(file.filename)
            try:
                current_app.logger.debug(
                    f"Testing file {image_path} for image {image.identifier}."
                )
                with WsiDicomizer.open(
                    image_path, include_confidential=False, metadata=metadata, **kwargs
                ) as wsi:
                    current_app.logger.debug(
                        f"Found file {image_path} for image {image.identifier}."
                    )
                    yield wsi
                    return
            except Exception as exception:
                current_app.logger.error(exception, exc_info=True)
                pass

        current_app.logger.error(
            f"No supported image file found for image {image.identifier} in {image.folder_path}."
        )
        yield
        return

    @contextmanager
    def _open_wsidicom(self, Image: Image, path: Path, **kwargs):
        try:
            with WsiDicom.open(path, **kwargs) as wsi:
                yield wsi
                return
        except Exception:
            yield None
            return


class StoreProcessingStep(ImageProcessingStep):
    """Step that moves the image to storage."""

    def __init__(self, use_pseudonyms: bool = True):
        self._use_pseudonyms = use_pseudonyms

    def run(self, storage: Storage, image: Image, path: Path) -> Path:
        current_app.logger.info(f"Moving image {image.uid} in {path} to outbox.")
        return storage.store_image(image, path, self._use_pseudonyms)


class DicomProcessingStep(ImageProcessingStep):
    """Step the converts image to dicom."""

    _tempdirs: Dict[UUID, TemporaryDirectory]

    def __init__(
        self,
        config: DicomizationConfig,
        use_pseudonyms: bool = False,
    ):
        self._config = config
        self._use_pseudonyms = use_pseudonyms
        self._tempdirs = {}

    def run(self, storage: Storage, image: Image, path: Path) -> Path:
        # TODO user should be able to control the metadata and conversion settings
        tempdir = TemporaryDirectory()
        self._tempdirs[image.uid] = tempdir
        dicom_name = str(image.uid)
        dicom_path = Path(tempdir.name).joinpath(dicom_name)
        os.makedirs(dicom_path)
        current_app.logger.info(
            f"Dicomizing image {image.uid} in {path} to {dicom_path} with settings {self._config}."
        )
        metadata = self._create_metadata(image)
        with self._open_wsidicomizer(image, path, metadata=metadata) as wsi:
            if wsi is None:
                raise ValueError(f"Did not find an input file for {image.identifier}.")
            try:
                files = wsi.save(
                    dicom_path,
                    include_levels=self._config.levels,
                    include_labels=self._config.include_labels,
                    include_overviews=self._config.include_overviews,
                    workers=self._config.threads,
                )
            except Exception:
                current_app.logger.error(
                    f"Failed to save to DICOM for {image.uid} in {path}.", exc_info=True
                )
                raise
            finally:
                # Should not be needed, but just in case
                wsi.close()
            current_app.logger.info(
                f"Saved dicom for {image.uid} in {path}. Created files {files}."
            )
        image.set_files(
            [ImageFile(str(file.relative_to(dicom_path))) for file in files]
        )
        return dicom_path

    def _create_metadata(self, image: Image) -> WsiDicomizerMetadata:
        return WsiDicomizerMetadata()

    def cleanup(self, image: Image):
        try:
            current_app.logger.info(
                f"Cleaning up DICOM dir  {self._tempdirs[image.uid]}."
            )
            self._tempdirs[image.uid].cleanup()
        except Exception:
            current_app.logger.error(
                f"Failed to clean up DICOM dir {self._tempdirs[image.uid]},",
                exc_info=True,
            )


class CreateThumbnails(ImageProcessingStep):
    """Step that creates jpeg thumbnail for image."""

    def __init__(
        self,
        use_pseudonyms: bool = True,
        format: str = "jpeg",
        size: int = 512,
    ):
        self._use_pseudonyms = use_pseudonyms
        self._format = format
        self._size = size

    def run(self, storage: Storage, image: Image, path: Path) -> Path:
        current_app.logger.debug(f"making thumbnail for {image.uid} in path {path}")
        with self._open_wsidicom(image, path) as wsi:
            if wsi is None:
                return path
                # raise ValueError(f"Did not find an input file for {image.identifier}.")
            try:
                width = min(wsi.size.width, self._size)
                height = min(wsi.size.height, self._size)
                thumbnail = wsi.read_thumbnail((width, height))
                thumbnail.load()
            except Exception:
                current_app.logger.error(
                    f"Failed to read thumbnail for {image.uid} in {path}.",
                    exc_info=True,
                )
                raise
            finally:
                # Should not be needed, but just in case
                wsi.close()

            with io.BytesIO() as output:
                thumbnail.save(output, self._format)
                thumbnail_path = storage.store_thumbnail(
                    image, output.getvalue(), self._use_pseudonyms
                )
                image.set_thumbnail_path(thumbnail_path)
            return path


class FinishingStep(ImageProcessingStep):
    def __init__(self, remove_source: bool = False):
        self._remove_source = remove_source

    def run(self, storage: Storage, image: Image, path: Path) -> Path:
        if self._remove_source:
            os.remove(image.folder_path)
        image.set_folder_path(path)
        current_app.logger.debug(
            f"Set image {image.uid} name {image.identifier} as {image.status}. "
            f"Project is {image.project.status}."
        )
        return path
