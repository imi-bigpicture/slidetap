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

from slidetap.database import DatabaseImage, DatabaseProject
from slidetap.model.session import UserSession
from slidetap.web.importer import ImageImporter


class DummyImageImporter(ImageImporter):
    def pre_process(self, session: UserSession, project: DatabaseProject):
        pass

    def redo_image_download(self, session: UserSession, image: DatabaseImage):
        pass

    def redo_image_pre_processing(self, image: DatabaseImage):
        pass

    def search(self, session: UserSession, project: DatabaseProject):
        pass
