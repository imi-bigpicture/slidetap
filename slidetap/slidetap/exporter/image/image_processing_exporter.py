from abc import abstractmethod

from slidetap.database.project import Image, Project
from slidetap.exporter.image.image_exporter import ImageExporter
from slidetap.image_processing.image_processor import ImageProcessor


class ImageProcessingExporter(ImageExporter):
    @property
    @abstractmethod
    def processor(self) -> ImageProcessor:
        raise NotImplementedError()

    def export(self, project: Project):
        """Should export the image to storage."""
        project.set_as_post_processing()
        images = Image.get_for_project(project.uid)
        for image in images:
            self._scheduler.add_job(
                str(image.uid),
                self.processor.run_job,
                {"image_uid": image.uid},
            )
