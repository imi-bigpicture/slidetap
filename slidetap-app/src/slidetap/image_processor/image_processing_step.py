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
import logging
import os
from abc import ABCMeta, abstractmethod
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, Generator, Optional, Tuple
from uuid import UUID, uuid4

from opentile.config import settings as opentile_settings
from wsidicom import WsiDicom
from wsidicomizer import WsiDicomizer
from wsidicomizer.metadata import WsiDicomizerMetadata

from slidetap.config import DicomizationConfig
from slidetap.model import Image, ImageFile, ImageFormat, Project, RootSchema
from slidetap.services import StorageService


class ImageProcessingStep(metaclass=ABCMeta):
    """Metaclass for an image processing step.

    Steps should not commit changes to the database. This is done when all the steps
    have been completed, so that the changes can be rolled back if an error occurs."""

    @abstractmethod
    def run(
        self,
        schema: RootSchema,
        storage_service: StorageService,
        project: Project,
        image: Image,
        path: Path,
    ) -> Tuple[Path, Image]:
        """Should implement the action of the processing step.

        Parameters
        ----------
        image: Image
            The image that is being processed.
        path: Path
            The path to the image file to process.
        """
        raise NotImplementedError()

    def cleanup(self, project: Project, image: Image):
        """Should implement any needed clean up to do after the processing
        step.

        Parameters
        ----------
        image: Image
            The image that should be cleaned up.
        """
        pass

    def _open_wsi(
        self,
        image: Image,
        path: Path,
        metadata: Optional[WsiDicomizerMetadata] = None,
        **kwargs,
    ):
        if image.format == ImageFormat.DICOM_WSI:
            return self._open_wsidicom(image, path, **kwargs)
        elif image.format == ImageFormat.OTHER_WSI:
            opentile_settings.ndpi_frame_cache = 4
            return self._open_wsidicomizer(image, path, metadata=metadata, **kwargs)
        else:
            return self._return_none()

    @contextmanager
    def _return_none(self):
        yield None

    @contextmanager
    def _open_wsidicomizer(
        self,
        image: Image,
        path: Path,
        metadata: Optional[WsiDicomizerMetadata] = None,
        **kwargs,
    ):
        if len(image.files) == 0:
            logging.error(f"No image files for image {image.identifier}")
            yield
            return
        for file in image.files:
            image_path = path.joinpath(file.filename)
            try:
                logging.debug(
                    f"Testing file {image_path} for image {image.identifier}."
                )
                wsi = WsiDicomizer.open(
                    image_path, include_confidential=False, metadata=metadata, **kwargs
                )
                logging.debug(f"Found file {image_path} for image {image.identifier}.")
                try:
                    yield wsi
                finally:
                    wsi.close()
                    return
            except Exception as exception:
                logging.error(exception, exc_info=True)
                pass

        logging.error(
            f"No supported image file found for image {image.identifier} in {image.folder_path}."
        )
        yield

    @contextmanager
    def _open_wsidicom(
        self, image: Image, path: Path, **kwargs
    ) -> Generator[Optional[WsiDicom], Any, None]:
        try:
            wsi = WsiDicom.open(path, **kwargs)
            try:
                yield wsi
            finally:
                wsi.close()
        except Exception:
            yield None


class StoreProcessingStep(ImageProcessingStep):
    """Step that moves the image to storage_service."""

    def __init__(self, use_pseudonyms: bool = True):
        self._use_pseudonyms = use_pseudonyms
        super().__init__()

    def run(
        self,
        schema: RootSchema,
        storage_service: StorageService,
        project: Project,
        image: Image,
        path: Path,
    ) -> Tuple[Path, Image]:
        logging.info(f"Moving image {image.uid} in {path} to outbox.")
        return (
            storage_service.store_image(project, image, path, self._use_pseudonyms),
            image,
        )


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

    def run(
        self,
        schema: RootSchema,
        storage_service: StorageService,
        project: Project,
        image: Image,
        path: Path,
    ) -> Tuple[Path, Image]:
        if image.format == ImageFormat.DICOM_WSI:
            logging.info(f"Image {image.uid} in {path} is already DICOM.")
            return path, image
        # TODO user should be able to control the metadata and conversion settings
        tempdir = TemporaryDirectory()
        self._tempdirs[image.uid] = tempdir
        dicom_name = str(image.uid)
        dicom_path = Path(tempdir.name).joinpath(dicom_name)
        os.makedirs(dicom_path)
        logging.info(
            f"Dicomizing image {image.uid} in {path} to {dicom_path} with settings {self._config}."
        )
        metadata = self._create_metadata(schema, image)
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
                logging.error(
                    f"Failed to save to DICOM for {image.uid} in {path}.", exc_info=True
                )
                raise
            finally:
                # Should not be needed, but just in case
                wsi.close()
            logging.info(
                f"Saved dicom for {image.uid} in {path}. Created files {files}."
            )
        image.files = [
            ImageFile(uid=uuid4(), filename=str(file.relative_to(dicom_path)))
            for file in files
        ]
        image.format = ImageFormat.DICOM_WSI
        return dicom_path, image

    def _create_metadata(
        self, schema: RootSchema, image: Image
    ) -> WsiDicomizerMetadata:
        return WsiDicomizerMetadata()

    def cleanup(self, project: Project, image: Image):
        try:
            logging.info(f"Cleaning up DICOM dir {self._tempdirs[image.uid]}.")
            self._tempdirs[image.uid].cleanup()
        except Exception:
            logging.error(
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

    def run(
        self,
        schema: RootSchema,
        storage_service: StorageService,
        project: Project,
        image: Image,
        path: Path,
    ) -> Tuple[Path, Image]:
        logging.debug(f"making thumbnail for {image.uid} in path {path}")
        with self._open_wsidicom(image, path) as wsi:
            if wsi is None:
                return path, image
                # raise ValueError(f"Did not find an input file for {image.identifier}.")
            try:
                width = min(wsi.size.width, self._size)
                height = min(wsi.size.height, self._size)
                thumbnail = wsi.read_thumbnail((width, height))
                thumbnail.load()
            except Exception:
                logging.error(
                    f"Failed to read thumbnail for {image.uid} in {path}.",
                    exc_info=True,
                )
                raise
            finally:
                # Should not be needed, but just in case
                wsi.close()

            with io.BytesIO() as output:
                thumbnail.save(output, self._format)
                thumbnail_path = storage_service.store_thumbnail(
                    project, image, output.getvalue(), self._use_pseudonyms
                )
                image.thumbnail_path = str(thumbnail_path)
            return path, image


class FinishingStep(ImageProcessingStep):
    def __init__(self, remove_source: bool = False):
        self._remove_source = remove_source

    def run(
        self,
        schema: RootSchema,
        storage_service: StorageService,
        project: Project,
        image: Image,
        path: Path,
    ) -> Tuple[Path, Image]:
        if (
            self._remove_source
            and image.folder_path is not None
            and Path(image.folder_path).exists()
        ):
            os.remove(image.folder_path)
        image.folder_path = None
        return path, image
