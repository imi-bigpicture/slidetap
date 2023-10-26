"""Implementation of image exporter that runs a series of processing steps."""
import io
import os
from abc import ABCMeta, abstractmethod
from contextlib import contextmanager
from logging import Logger
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, Iterable, List, Optional
from uuid import UUID

from flask import Flask, current_app
from pydicom import Dataset
from wsidicom import WsiDicom
from wsidicomizer import WsiDicomizer
from wsidicomizer.dataset import (
    create_brightfield_optical_path_module,
    create_device_module,
    create_patient_module,
    create_specimen_module,
    create_study_module,
)

from slidetap.database import Image, ImageFile, SampleSchema, db
from slidetap.exporter.image.image_exporter import ImageExporter
from slidetap.storage import Storage


class ImageProcessingStep(metaclass=ABCMeta):
    """Metaclass for an image processing step."""

    def __init__(self, app: Optional[Flask] = None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask):
        self._logger = app.logger

    @property
    def logger(self) -> Logger:
        return self._logger

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
    def _open_wsidicomizer(self, image: Image, path: Path, **kwargs):
        if len(image.files) == 0:
            current_app.logger.debug(f"No image files for image {image.name}")
            yield
        for file in image.files:
            image_path = path.joinpath(file.filename)
            try:
                current_app.logger.debug(
                    f"Testing file {image_path} for image {image.name}."
                )
                with WsiDicomizer.open(image_path, **kwargs) as wsi:
                    current_app.logger.debug(
                        f"Found file {image_path} for image {image.name}."
                    )
                    yield wsi
                    return
            except Exception as exception:
                current_app.logger.debug(exception, exc_info=True)
                pass

        current_app.logger.debug(
            f"No supported image file found for image {image.name} in {image.folder_path}."
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

    def __init__(self, uid_folders: bool = False, app: Optional[Flask] = None):
        super().__init__(app)
        self._uid_folders = uid_folders

    def run(self, storage: Storage, image: Image, path: Path) -> Path:
        current_app.logger.info(f"Moving image {image.uid} in {path} to outbox.")
        return storage.store_image(image, path, self._uid_folders)


class DicomProcessingStep(ImageProcessingStep):
    """Step the converts image to dicom."""

    _tempdirs: Dict[UUID, TemporaryDirectory]

    def __init__(self, app: Optional[Flask] = None):
        super().__init__(app)
        self._tempdirs = {}

    def run(self, storage: Storage, image: Image, path: Path) -> Path:
        # TODO user should be able to control the metadata and conversion settings
        tempdir = TemporaryDirectory()
        self._tempdirs[image.uid] = tempdir
        dicom_path = Path(tempdir.name).joinpath(image.name)
        os.makedirs(dicom_path)
        current_app.logger.info(
            f"Dicomizing image {image.uid} in {path} to {dicom_path}."
        )
        modules: List[Dataset] = []
        device_module = create_device_module(manufacturer="Hamamatsu")
        modules.append(device_module)
        optical_path_module = create_brightfield_optical_path_module()
        modules.append(optical_path_module)
        if len(image.samples) != 0:
            specimen_module = create_specimen_module(
                slide_id=str(image.samples[0].uid), samples=[]
            )
            modules.append(specimen_module)
            try:
                biological_being_schema = SampleSchema.get(
                    image.project.schema, "biological_being"
                )
                biological_being = image.samples[0].get_parents_of_type(
                    biological_being_schema,
                    True,
                )[0]
                sex = biological_being.get_attribute("sex").value
                if str(sex).lower in ["male", "m"]:
                    sex = "M"
                elif str(sex).lower in ["female", "f"]:
                    sex = "F"
                elif str(sex).lower in ["other", "o"]:
                    sex = "O"
                else:
                    sex = ""
                patient_module = create_patient_module(
                    id=str(biological_being),
                    sex=sex,
                )
                modules.append(patient_module)
            except IndexError:
                pass

        study_module = create_study_module()
        modules.append(study_module)
        with self._open_wsidicomizer(
            image,
            path,
            modules=modules,
            # include_levels=[-1]
        ) as wsi:
            if wsi is None:
                raise ValueError(f"Did not find an input file for {image.name}.")
            files = wsi.save(dicom_path)
            current_app.logger.debug(files)
        image.set_files(
            [ImageFile(str(file.relative_to(dicom_path))) for file in files]
        )
        return dicom_path

    def cleanup(self, image: Image):
        try:
            self._tempdirs[image.uid].cleanup()
        except Exception:
            current_app.logger.error(
                f"Failed to clean up dicom dir {self._tempdirs[image.uid]},",
                exc_info=True,
            )


class CreateThumbnails(ImageProcessingStep):
    """Step that creates jpeg thumbnail for image."""

    def __init__(
        self,
        uid_names: bool = False,
        format: str = "jpeg",
        size: int = 512,
        app: Optional[Flask] = None,
    ):
        super().__init__(app)
        self._uid_names = uid_names
        self._format = format
        self._size = size

    def run(self, storage: Storage, image: Image, path: Path) -> Path:
        current_app.logger.info(f"making thumbnail for {image.uid} in path {path}")
        for reader in (self._open_wsidicom, self._open_wsidicomizer):
            with reader(image, path) as wsi:
                if wsi is None:
                    continue
                thumbnail = wsi.read_thumbnail((self._size, self._size))
                with io.BytesIO() as output:
                    thumbnail.save(output, self._format)
                    thumbnail_path = storage.store_thumbnail(
                        image, output.getvalue(), self._uid_names
                    )
                    image.set_thumbnail_path(thumbnail_path)
                return path
        raise ValueError("Did not find a image to make a thumbnail for.")


class FinishingStep(ImageProcessingStep):
    def __init__(self, remove_source: bool = False, app: Optional[Flask] = None):
        super().__init__(app)
        self._remove_source = remove_source

    def run(self, storage: Storage, image: Image, path: Path) -> Path:
        image.set_as_completed()
        if self._remove_source:
            os.remove(image.folder_path)
        image.set_folder_path(path)
        image.project.set_status_if_finished()
        current_app.logger.info(
            f"Set image {image.uid} name {image.name} as {image.status}. "
            f"Project is {image.project.status}."
        )
        return path


class StepImageExporter(ImageExporter):
    """Image exporter that runs a sequence of steps on the processing image."""

    _steps: Iterable[ImageProcessingStep]

    def __init__(
        self,
        storage: Storage,
        steps: Iterable[ImageProcessingStep],
        finishing_step: ImageProcessingStep = FinishingStep(),
        app: Optional[Flask] = None,
    ):
        """Create a DefaultImageProcessor.

        Parameters
        ----------
        storage: Storage
        steps: Iterable[ImageProcessingStep]
        finishing_step: ImageProcessingStep = FinishingStep()
        app: Optional[Flask] = None
        """
        self._steps = list(steps)
        self._steps.append(finishing_step)
        super().__init__(storage, app)

    def init_app(self, app: Flask):
        super().init_app(app)
        for step in self._steps:
            step.init_app(app)

    def _run_job(
        self,
        image_uid: UUID,
    ):
        if not isinstance(self._scheduler.app, Flask):
            raise RuntimeError("init_app() must be run before using exporter.")
        with self._scheduler.app.app_context():
            with db.session.no_autoflush:
                image = Image.get(image_uid)
                assert image is not None
                image.set_as_processing()
                current_app.logger.info(
                    (
                        f"Processing image {image.uid}, name {image.name}, "
                        f"status: {image.status}, folder: {image.folder_path}."
                    )
                )
                processing_path = Path(image.folder_path)
                try:
                    for step in self._steps:
                        processing_path = step.run(self.storage, image, processing_path)
                except Exception:
                    current_app.logger.error(
                        f"Processing failed for {image.uid} name {image.name}.",
                        exc_info=True,
                    )
                    image.set_as_failed()
                current_app.logger.info(f"Cleanup {image.uid} name {image.name}.")
                for step in self._steps:
                    step.cleanup(image)
