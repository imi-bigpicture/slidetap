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
from typing import Optional

from slidetap.model import Dataset, Item, Project


class MetadataExportInterface(metaclass=ABCMeta):
    """
    Metaclass for interface for exporting metadata. Implementations must implement:
    - preview_item: Return a serialized representation of the item.
    - export: Serialize all metadata for the project to storage.
    """

    @abstractmethod
    def preview_item(self, item: Item) -> Optional[str]:
        """
        Return a serialized representation of the item.

        Parameters
        ----------
        item: Item
            The item to serialize.
        """
        raise NotImplementedError()

    @abstractmethod
    def export(self, project: Project, dataset: Dataset) -> None:
        """
        Export metadata for the project to storage.

        Must throw an exception if the metadata cannot be exported.

        Parameters
        ----------
        project: Project
            The project to export metadata for.
        dataset: Dataset
            The dataset to export metadata for.
        """
        raise NotImplementedError()
