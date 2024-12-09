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

"""Service for accessing attributes."""

from typing import Dict, Iterable, Optional, TypeVar, Union
from uuid import UUID

from slidetap.database import (
    DatabaseAnnotation,
    DatabaseAnnotationSchema,
    DatabaseImage,
    DatabaseImageSchema,
    DatabaseItem,
    DatabaseItemSchema,
    DatabaseObservation,
    DatabaseObservationSchema,
    DatabaseProject,
    DatabaseSample,
    DatabaseSampleSchema,
    db,
)
from slidetap.model.item import Annotation, Image, Item, Observation, Sample
from slidetap.model.schema.item_schema import ItemSchema
from slidetap.model.table import ColumnSort
from slidetap.services.attribute_service import AttributeService
from slidetap.services.mapper_service import MapperService
from slidetap.services.validation_service import ValidationService

ItemType = TypeVar("ItemType", bound=Item)


class ItemService:
    """Item service should be used to interface with items"""

    def __init__(
        self,
        attribute_service: AttributeService,
        mapper_service: MapperService,
        validation_service: ValidationService,
    ) -> None:
        self._attribute_service = attribute_service
        self._mapper_service = mapper_service
        self._validation_service = validation_service

    def get(self, item_uid: UUID) -> Optional[Item]:
        item = DatabaseItem.get_optional(item_uid)
        if item is None:
            return None
        return item.model

    def select(self, item_uid: UUID, value: bool) -> Optional[Item]:
        item = DatabaseItem.get_optional(item_uid)
        if item is None:
            return None
        item.set_select(value)
        self._validation_service.validate_item_relations(item)
        return item.model

    def get_schema_for_item(self, item_uid: UUID) -> Optional[ItemSchema]:
        item = DatabaseItem.get_optional(item_uid)
        if item is None:
            return None
        return item.schema.model

    def update(self, item: Item) -> Optional[Item]:
        existing_item = DatabaseItem.get_optional(item.uid)
        if existing_item is None:
            return None
        existing_item.set_name(item.name)
        existing_item.set_identifier(item.identifier)
        if isinstance(existing_item, DatabaseSample):
            if not isinstance(item, Sample):
                raise TypeError(f"Expected Sample, got {type(item)}.")
            existing_item.set_parents(
                DatabaseSample.get(parent.uid) for parent in item.parents
            )
            existing_item.set_children(
                DatabaseSample.get(child.uid) for child in item.children
            )
        elif isinstance(existing_item, DatabaseImage):
            if not isinstance(item, DatabaseImage):
                raise TypeError(f"Expected Image, got {type(item)}.")
            existing_item.set_samples(
                DatabaseSample.get(sample.uid) for sample in item.samples
            )
        elif isinstance(existing_item, DatabaseAnnotation):
            if not isinstance(item, DatabaseAnnotation):
                raise TypeError(f"Expected Annotation, got {type(item)}.")
            existing_item.set_image(
                DatabaseImage.get(item.image.uid) if item.image else None
            )

        elif isinstance(existing_item, DatabaseObservation):
            if not isinstance(item, DatabaseObservation):
                raise TypeError(f"Expected Observation, got {type(item)}.")
            observation_item = DatabaseItem.get(item.item.uid)
            if not isinstance(
                observation_item, (DatabaseImage, DatabaseSample, DatabaseAnnotation)
            ):
                raise ValueError(f"Item {item.item.uid} not found.")
            existing_item.set_item(observation_item)
        else:
            raise TypeError(f"Unknown item type {existing_item}.")
        self._attribute_service.update_for_item(existing_item, item.attributes)
        self._validation_service.validate_item_relations(existing_item)

    def add(self, item: ItemType) -> ItemType:
        project = DatabaseProject.get(item.project_uid)

        if isinstance(item, Sample):
            schema = DatabaseSampleSchema.get(item.schema_uid)
            database_item = DatabaseSample(
                project,
                schema,
                item.identifier,
                parents=[DatabaseSample.get(parent.uid) for parent in item.parents],
                children=[DatabaseSample.get(child.uid) for child in item.children],
                commit=False,
            )
        elif isinstance(item, Image):
            schema = DatabaseImageSchema.get(item.schema_uid)
            database_item = DatabaseImage(
                project,
                schema,
                item.identifier,
                samples=[DatabaseSample.get(sample.uid) for sample in item.samples],
                commit=False,
            )
        elif isinstance(item, Annotation):
            schema = DatabaseAnnotationSchema.get(item.schema_uid)
            database_item = DatabaseAnnotation(
                project,
                schema,
                item.identifier,
                image=DatabaseImage.get(item.image.uid) if item.image else None,
                commit=False,
            )
        elif isinstance(item, Observation):
            schema = DatabaseObservationSchema.get(item.schema_uid)
            if item.item is None:
                raise ValueError("Observation must have an item to observe.")
            observation_item = DatabaseItem.get(item.item.uid)
            if not isinstance(
                observation_item, (DatabaseImage, DatabaseSample, DatabaseAnnotation)
            ):
                raise ValueError(f"Item {item.item.uid} not found.")
            database_item = DatabaseObservation(
                project,
                schema,
                item.identifier,
                observation_item,
                commit=False,
            )
        else:
            raise TypeError(f"Unknown item type {item}.")
        self._attribute_service.create_for_item(
            database_item, item.attributes, commit=False
        )
        self._validation_service.validate_item_relations(database_item)
        self._mapper_service.apply_mappers_to_item(database_item, commit=False)
        db.session.commit()
        return database_item.model  # type: ignore

    def copy(self, item_uid: UUID) -> Optional[Item]:
        item = DatabaseItem.get_optional(item_uid)
        if item is None:
            return None
        assert isinstance(
            item,
            (DatabaseSample, DatabaseImage, DatabaseObservation, DatabaseAnnotation),
        )
        return item.copy().model

    def create(
        self, item_schema: Union[UUID, ItemSchema], project_uid: UUID
    ) -> Optional[Item]:
        if isinstance(item_schema, UUID):
            database_schema = DatabaseItemSchema.get(item_schema)
        else:
            database_schema = DatabaseItemSchema.get(item_schema.uid)
        if database_schema is None:
            return None
        project = DatabaseProject.get_optional(project_uid)
        if project is None:
            return None

        if isinstance(database_schema, DatabaseSampleSchema):
            return DatabaseSample(
                project,
                database_schema,
                "New sample",
                [],
                [],
                add=False,
                commit=False,
            ).model
        if isinstance(database_schema, DatabaseImageSchema):
            return DatabaseImage(
                project,
                database_schema,
                "New image",
                [],
                add=False,
                commit=False,
            ).model
        if isinstance(database_schema, DatabaseAnnotationSchema):
            return DatabaseAnnotation(
                project,
                database_schema,
                "New annotation",
                None,
                add=False,
                commit=False,
            ).model
        if isinstance(database_schema, DatabaseObservationSchema):
            return DatabaseObservation(
                project,
                database_schema,
                "New observation",
                None,
                add=False,
                commit=False,
            ).model
        raise TypeError(f"Unknown item schema {database_schema}.")

    def get_for_schema(
        self,
        item_schema_uid: UUID,
        project_uid: UUID,
        start: Optional[int] = None,
        size: Optional[int] = None,
        identifier_filter: Optional[str] = None,
        attribute_filters: Optional[Dict[str, str]] = None,
        sorting: Optional[Iterable[ColumnSort]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> Iterable[Item]:
        item_schema = DatabaseItemSchema.get(item_schema_uid)
        if isinstance(item_schema, DatabaseSampleSchema):
            item_class = DatabaseSample
        elif isinstance(item_schema, DatabaseImageSchema):
            item_class = DatabaseImage
        elif isinstance(item_schema, DatabaseAnnotationSchema):
            item_class = DatabaseAnnotation
        elif isinstance(item_schema, DatabaseObservationSchema):
            item_class = DatabaseObservation
        else:
            raise TypeError(f"Unknown item type {item_schema}.")

        return (
            item.model
            for item in item_class.get_for_project(
                project_uid,
                item_schema,
                start,
                size,
                identifier_filter,
                attribute_filters,
                sorting,
                selected,
                valid,
            )
        )

    def get_count_for_schema(
        self,
        item_schema_uid: UUID,
        project_uid: UUID,
        identifier_filter: Optional[str] = None,
        attribute_filters: Optional[Dict[str, str]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> int:
        return DatabaseItem.get_count_for_project(
            project_uid,
            item_schema_uid,
            identifier_filter,
            attribute_filters,
            selected=selected,
            valid=valid,
        )
