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

"""Metaclass for metadata importer."""

from abc import ABCMeta, abstractmethod
from typing import Union

from werkzeug.datastructures import FileStorage

from slidetap.database import Project, Schema
from slidetap.importer.importer import Importer
from slidetap.model import Session


class MetadataImporter(Importer, metaclass=ABCMeta):
    """Metaclass for metadata importer."""

    @property
    @abstractmethod
    def schema(self) -> Schema:
        """Should return the schema used for returned metadata."""
        raise NotImplementedError()

    @abstractmethod
    def create_project(self, session: Session, name: str) -> Project:
        """Should create a new project and return it."""
        raise NotImplementedError()

    @abstractmethod
    def search(
        self, session: Session, project: Project, file: Union[FileStorage, bytes]
    ):
        """Should search for metadata based on search criteria defined in
        file, and add found metadata to project."""
        raise NotImplementedError()
