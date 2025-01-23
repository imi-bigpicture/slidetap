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

from slidetap.database import db
from slidetap.database.project import DatabaseDataset
from slidetap.importer.dataset_importer import DatasetImporter
from slidetap.model import Dataset
from slidetap.services.schema_service import SchemaService
from slidetap.services.validation_service import ValidationService


class DatasetService:
    def __init__(
        self,
        # dataset_importer: DatasetImporter,
        validation_service: ValidationService,
        schema_service: SchemaService,
    ):
        # self._dataset_importer = dataset_importer
        self._validation_service = validation_service
        self._schema_service = schema_service

    # def get_importable_datasets(self):
    #     return self._dataset_importer.get_importable_datasets()

    # def import_dataset(self, dataset: Dataset):
    #     return self._dataset_importer.import_dataset(dataset)

    def create(self, dataset: Dataset):
        database_dataset = DatabaseDataset.get_or_create_from_model(
            dataset, self._schema_service.root.dataset
        )
        self._validation_service.validate_dataset_attributes(database_dataset)
        db.session.commit()
        return database_dataset.model
