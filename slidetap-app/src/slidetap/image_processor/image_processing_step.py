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
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
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

    def __init__(self):
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def run(
        self,
        schema: RootSchema,
        storage_service: StorageService,
        project: Project,
        image: Image,
        path: Path,
        working_folder: Path,
        task_id: str,
    ) -> tuple[Path, Image]:
        """Should implement the action of the processing step.

        Parameters
        ----------
        schema: RootSchema
            The root schema for the project.
        storage_service: StorageService
            The storage service to use for storing files.
        project: Project
            The project that the image belongs to.
        image: Image
            The image that is being processed.
        path: Path
            The path to the image file to process.
        working_folder: Path
            Step-specific temporary working folder. Will be purged after all
            steps are done.
        task_id: str
            The task ID, used to isolate processing output per task.

        Returns
        -------
        tuple[Path, Image]
            The path to the processed image file and the updated image. The path can be
            within the working folder.
        """
        raise NotImplementedError()

    def cleanup(self, project: Project, image: Image) -> None:  # noqa
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
        metadata: WsiDicomizerMetadata | None = None,
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
        metadata: WsiDicomizerMetadata | None = None,
        **kwargs,
    ):
        if len(image.files) == 0:
            self._logger.error(f"No image files for image {image.identifier}")
            yield None
            return
        for file in image.files:
            image_path = path.joinpath(file.filename)
            self._logger.debug(
                f"Testing file {image_path} for image {image.identifier}."
            )
            try:
                wsi = WsiDicomizer.open(
                    image_path, include_confidential=False, metadata=metadata, **kwargs
                )
            except Exception as exception:
                self._logger.error(exception, exc_info=True)
                continue
            self._logger.debug(f"Found file {image_path} for image {image.identifier}.")
            try:
                yield wsi
            finally:
                try:
                    wsi.close()
                except Exception:
                    self._logger.exception(
                        f"Error closing wsi for image {image.identifier}"
                    )
            return

        self._logger.error(
            f"No supported image file found for image {image.identifier} "
            f"in {image.folder_path}."
        )
        yield None

    @contextmanager
    def _open_wsidicom(
        self, image: Image, path: Path, **kwargs
    ) -> Generator[WsiDicom | None, Any, None]:
        try:
            wsi = WsiDicom.open(path, **kwargs)
        except Exception:
            self._logger.error(
                f"Failed to open WsiDicom for image {image.identifier}", exc_info=True
            )
            yield None
            return
        try:
            yield wsi
        finally:
            try:
                wsi.close()
            except Exception:
                self._logger.exception(
                    f"Error closing wsi for image {image.identifier}"
                )


class StoreProcessingStep(ImageProcessingStep):
    """Step that moves the image to the processing directory."""

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
        working_folder: Path,
        task_id: str,
    ) -> tuple[Path, Image]:
        self._logger.info(f"Moving image {image.uid} in {path} to processing dir.")
        return (
            storage_service.store_image_to_processing(
                project, image, path, task_id, self._use_pseudonyms
            ),
            image,
        )


class DicomProcessingStep(ImageProcessingStep):
    """Step the converts image to dicom."""

    _tempdirs: dict[UUID, TemporaryDirectory]

    def __init__(
        self,
        config: DicomizationConfig,
        use_pseudonyms: bool = False,
    ):
        self._config = config
        self._use_pseudonyms = use_pseudonyms
        self._tempdirs = {}
        super().__init__()

    def run(
        self,
        schema: RootSchema,
        storage_service: StorageService,
        project: Project,
        image: Image,
        path: Path,
        working_folder: Path,
        task_id: str,
    ) -> tuple[Path, Image]:
        # TODO user should be able to control the metadata and conversion settings
        dicom_name = str(image.uid)
        dicom_path = working_folder.joinpath(dicom_name)
        os.makedirs(dicom_path)
        metadata = self._create_metadata(schema, image)
        if image.format == ImageFormat.DICOM_WSI:
            self._logger.info(
                f"De-identifying DICOM image {image.uid} in {path} to {dicom_path}."
            )
            files = self._resave_dicom(image, path, dicom_path, metadata)
        else:
            self._logger.info(
                f"Dicomizing image {image.uid} in {path} to {dicom_path} "
                f"with settings {self._config}."
            )
            files = self._dicomize(image, path, dicom_path, metadata)
        image.files = [
            ImageFile(uid=uuid4(), filename=str(file.relative_to(dicom_path)))
            for file in files
        ]
        image.format = ImageFormat.DICOM_WSI
        return dicom_path, image

    def _dicomize(
        self,
        image: Image,
        path: Path,
        dicom_path: Path,
        metadata: WsiDicomizerMetadata,
    ) -> list[Path]:
        """Convert a non-DICOM image to DICOM using the created metadata."""
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
                self._logger.error(
                    f"Failed to save to DICOM for {image.uid} in {path}.", exc_info=True
                )
                raise
            finally:
                # Should not be needed, but just in case
                wsi.close()
            self._logger.info(
                f"Saved dicom for {image.uid} in {path}. Created files {files}."
            )
            return [Path(file) for file in files]

    def _resave_dicom(
        self,
        image: Image,
        path: Path,
        dicom_path: Path,
        metadata: WsiDicomizerMetadata,
    ) -> list[Path]:
        """Re-save an already-DICOM image, rewriting its metadata.

        The created metadata is merged on top of the metadata read from the
        source image, and the result replaces the source metadata so that
        attributes not modeled by the metadata schema (e.g. private tags) are
        dropped. Confidential metadata from the source is always removed.
        """
        with self._open_wsidicom(image, path) as wsi:
            if wsi is None:
                raise ValueError(f"Did not find an input file for {image.identifier}.")
            source = wsi.metadata
            base = WsiDicomizerMetadata(
                study=source.study,
                series=source.series,
                patient=source.patient,
                equipment=source.equipment,
                pyramid=source.pyramid,
                slide=source.slide,
                label=source.label,
                overview=source.overview,
                frame_of_reference_uid=source.frame_of_reference_uid,
                dimension_organization_uids=source.dimension_organization_uids,
            )
            deidentified = base.merge(metadata, None, include_confidential=False)
            try:
                files = wsi.save(
                    dicom_path,
                    metadata=deidentified,
                    replace_metadata=True,
                    include_levels=self._config.levels,
                    include_labels=self._config.include_labels,
                    include_overviews=self._config.include_overviews,
                    workers=self._config.threads,
                )
            except Exception:
                self._logger.error(
                    f"Failed to re-save DICOM for {image.uid} in {path}.",
                    exc_info=True,
                )
                raise
            finally:
                # Should not be needed, but just in case
                wsi.close()
            self._logger.info(
                f"Re-saved DICOM for {image.uid} in {path}. Created files {files}."
            )
            return [Path(file) for file in files]

    def _create_metadata(
        self, schema: RootSchema, image: Image
    ) -> WsiDicomizerMetadata:
        """Create basic WsiDicomizerMetadata. Override to customize metadata."""
        return WsiDicomizerMetadata()


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
        super().__init__()

    def run(
        self,
        schema: RootSchema,
        storage_service: StorageService,
        project: Project,
        image: Image,
        path: Path,
        working_folder: Path,
        task_id: str,
    ) -> tuple[Path, Image]:
        self._logger.debug(f"making thumbnail for {image.uid} in path {path}")
        with self._open_wsidicom(image, path) as wsi:
            if wsi is None:
                return path, image
            try:
                width = min(wsi.size.width, self._size)
                height = min(wsi.size.height, self._size)
                thumbnail = wsi.read_thumbnail((width, height))
                thumbnail.load()
            except Exception:
                self._logger.error(
                    f"Failed to read thumbnail for {image.uid} in {path}.",
                    exc_info=True,
                )
                raise
            finally:
                # Should not be needed, but just in case
                wsi.close()

            with io.BytesIO() as output:
                thumbnail.save(output, self._format)
                thumbnail_path = storage_service.store_thumbnail_to_processing(
                    project,
                    image,
                    output.getvalue(),
                    task_id,
                    self._use_pseudonyms,
                )
                image.thumbnail_path = str(thumbnail_path)
            return path, image


class FinishingStep(ImageProcessingStep):
    def __init__(self, remove_source: bool = False):
        self._remove_source = remove_source
        super().__init__()

    def run(
        self,
        schema: RootSchema,
        storage_service: StorageService,
        project: Project,
        image: Image,
        path: Path,
        working_folder: Path,
        task_id: str,
    ) -> tuple[Path, Image]:
        if (
            self._remove_source
            and image.folder_path is not None
            and Path(image.folder_path).exists()
        ):
            os.remove(image.folder_path)
        image.folder_path = None
        return path, image
