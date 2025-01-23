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

from uuid import UUID

from slidetap.database import DatabaseImage
from slidetap.exporter import ImageExporter


class DummyImageExporter(ImageExporter):
    def export(self, project_uid: UUID):
        pass

    def re_export(self, image: DatabaseImage):
        pass

    def add_job(self, image_uid: UUID):
        pass
