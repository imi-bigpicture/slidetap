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

from typing import Optional

from slidetap.importer.dataset_importer import DatasetImporter
from slidetap.model import Dataset
from slidetap.services.database_service import DatabaseService
from slidetap.services.schema_service import SchemaService
from slidetap.services.validation_service import ValidationService
from sqlalchemy.orm import Session


class DatasetService:
    def __init__(
        self,
        # dataset_importer: DatasetImporter,
        validation_service: ValidationService,
        schema_service: SchemaService,
        database_service: DatabaseService,
    ):
        # self._dataset_importer = dataset_importer
        self._validation_service = validation_service
        self._schema_service = schema_service
        self._database_service = database_service

    # def get_importable_datasets(self):
    #     return self._dataset_importer.get_importable_datasets()

    # def import_dataset(self, dataset: Dataset):
    #     return self._dataset_importer.import_dataset(dataset)

    def create(self, dataset: Dataset, session: Optional[Session] = None) -> Dataset:
        with self._database_service.get_session(session) as session:
            existing = self._database_service.get_optional_dataset(session, dataset)
            if existing:
                return existing.model
            database_dataset = self._database_service.add_dataset(
                session, dataset, False
            )
            self._validation_service.validate_dataset_attributes(
                database_dataset, session
            )
            session.commit()
            return database_dataset.model
