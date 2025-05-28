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
from uuid import UUID

from sqlalchemy.orm import Session

from slidetap.model import Dataset
from slidetap.services.attribute_service import AttributeService
from slidetap.services.database_service import DatabaseService
from slidetap.services.mapper_service import MapperService
from slidetap.services.schema_service import SchemaService
from slidetap.services.validation_service import ValidationService


class DatasetService:
    def __init__(
        self,
        attribute_service: AttributeService,
        schema_service: SchemaService,
        validation_service: ValidationService,
        mapper_service: MapperService,
        database_service: DatabaseService,
    ):
        self._attribute_service = attribute_service
        self._schema_service = schema_service
        self._validation_service = validation_service
        self._mapper_service = mapper_service
        self._database_service = database_service

    def create(
        self,
        dataset: Dataset,
        mappers: Iterable[UUID],
        session: Optional[Session] = None,
    ) -> Dataset:
        with self._database_service.get_session(session) as session:
            existing = self._database_service.get_optional_dataset(session, dataset)
            if existing:
                return existing.model
            database_dataset = self._database_service.add_dataset(session, dataset)
            database_dataset.attributes = (
                self._attribute_service.create_or_update_attributes(
                    dataset.attributes, session=session
                )
            )
            self._mapper_service.apply_mappers_to_attributes(
                database_dataset.attributes, mappers, validate=False
            )
            self._validation_service.validate_dataset_attributes(
                database_dataset, session=session
            )

            session.commit()
            return database_dataset.model

    def get(self, uid: UUID, session: Optional[Session] = None) -> Optional[Dataset]:
        with self._database_service.get_session(session) as session:
            database_dataset = self._database_service.get_dataset(session, uid)
            if database_dataset is None:
                return None
            return database_dataset.model
