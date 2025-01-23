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
from pathlib import Path
from typing import Any, Dict

from slidetap.task.processors.processor import Processor


class DatasetImportProcessor(Processor, metaclass=ABCMeta):
    @abstractmethod
    def run(self, path: Path, **kwargs: Dict[str, Any]):
        """Should import the metadata in project to storage."""
        raise NotImplementedError()
