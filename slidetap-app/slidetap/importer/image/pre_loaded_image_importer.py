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

from slidetap.database.project import Image, Project
from slidetap.database.schema.item_schema import ImageSchema
from slidetap.importer.image.image_processing_importer import ImageProcessingImporter
from slidetap.model.session import Session


class PreLoadedImageImporter(ImageProcessingImporter):
    """Image importer that just runs the pre-processor on all loaded images."""

    def pre_process(self, session: Session, project: Project):
        image_schema = ImageSchema.get(project.root_schema, "wsi")
        for image in Image.get_for_project(
            project.uid, image_schema.uid, selected=True
        ):
            self._scheduler.add_job(
                str(image.uid),
                self.processor.run,
                job_parameters={"image_uid": image.uid},
            )

    def redo_image_pre_processing(self, image: Image):
        pass

    def redo_image_download(self, session: Session, image: Image):
        self.pre_process(session, image.project)
