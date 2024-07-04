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
from uuid import UUID

from slidetap.flask_extension import FlaskExtension


class MetadataImportProcessor(FlaskExtension, metaclass=ABCMeta):
    """Metaclass for metadata project importer."""

    @abstractmethod
    def run(self, project_uid: UUID, **kwargs):
        """Should import the metadata in project to storage."""
        raise NotImplementedError()
