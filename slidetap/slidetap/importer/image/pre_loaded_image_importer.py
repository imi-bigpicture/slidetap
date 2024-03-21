from slidetap.database.project import Image, Project
from slidetap.database.schema.item_schema import ImageSchema
from slidetap.importer.image.image_processing_importer import ImageProcessingImporter
from slidetap.model.session import Session


class PreLoadedImageImporter(ImageProcessingImporter):
    """Image importer that just runs the pre-processor on all loaded images."""

    def preprocess(self, session: Session, project: Project):
        image_schema = ImageSchema.get(project.root_schema, "wsi")
        for image in Image.get_for_project(
            project.uid, image_schema.uid, selected=True
        ):
            self._scheduler.add_job(
                str(image.uid),
                self.processor.run,
                job_parameters={"image_uid": image.uid},
            )
