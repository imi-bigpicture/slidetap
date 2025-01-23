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

from typing import Iterable, Optional

from flask import Flask
from slidetap.importer.dataset_importer import BackgroundDatasetImporter
from slidetap.model.dataset import ImportableDataset
from slidetap.storage.storage import Storage
from slidetap.task.scheduler import Scheduler


class JsonDatasetImporter(BackgroundDatasetImporter):
    def __init__(
        self, storage: Storage, scheduler: Scheduler, app: Optional[Flask] = None
    ):
        self._storage = storage
        super().__init__(scheduler, app)

    def _get_importable_datasets(self) -> Iterable[ImportableDataset]:
        raise NotImplementedError()
