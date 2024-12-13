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

from typing import Dict, Iterable, Optional, Sequence, Union
from uuid import UUID

from slidetap.database import (
    DatabaseAnnotation,
    DatabaseAnnotationSchema,
    DatabaseAttribute,
    DatabaseImage,
    DatabaseImageSchema,
    DatabaseItem,
    DatabaseItemSchema,
    DatabaseObservation,
    DatabaseObservationSchema,
    DatabaseSample,
    DatabaseSampleSchema,
    db,
)
from slidetap.model import (
    Annotation,
    ColumnSort,
    Image,
    Item,
    ItemSchema,
    ItemType,
    Observation,
    Sample,
)
from slidetap.services.attribute_service import AttributeService
from slidetap.services.database_service import DatabaseService
from slidetap.services.mapper_service import MapperService
from slidetap.services.validation_service import ValidationService


class ItemService:
    """Item service should be used to interface with items"""

    def __init__(
        self,
        attribute_service: AttributeService,
        mapper_service: MapperService,
        validation_service: ValidationService,
        database_service: DatabaseService,
    ) -> None:
        self._attribute_service = attribute_service
        self._mapper_service = mapper_service
        self._validation_service = validation_service
        self._database_service = database_service

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
                DatabaseSample.get(parent) for parent in item.parents
            )
            existing_item.set_children(
                DatabaseSample.get(child) for child in item.children
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

    def add_and_return_model(self, item: ItemType) -> ItemType:
        return self.add(item).model

    def add(self, item: ItemType, commit: bool = True) -> DatabaseItem[ItemType]:
        project = self._database_service.get_project(item.project_uid)
        if isinstance(item, Sample):
            schema = DatabaseSampleSchema.get(item.schema_uid)
            database_item = DatabaseSample(
                project,
                schema,
                item.identifier,
                parents=[DatabaseSample.get(parent) for parent in item.parents],
                children=[DatabaseSample.get(child) for child in item.children],
                uid=item.uid,
                commit=False,
            )
        elif isinstance(item, Image):
            schema = DatabaseImageSchema.get(item.schema_uid)
            database_item = DatabaseImage(
                project,
                schema,
                item.identifier,
                samples=[DatabaseSample.get(sample) for sample in item.samples],
                uid=item.uid,
                commit=False,
            )
        elif isinstance(item, Annotation):
            schema = DatabaseAnnotationSchema.get(item.schema_uid)
            database_item = DatabaseAnnotation(
                project,
                schema,
                item.identifier,
                image=DatabaseImage.get(item.image) if item.image else None,
                uid=item.uid,
                commit=False,
            )
        elif isinstance(item, Observation):
            schema = DatabaseObservationSchema.get(item.schema_uid)
            if item.sample is not None:
                observation_item = DatabaseSample.get(item.sample)
            elif item.image is not None:
                observation_item = DatabaseImage.get(item.image)
            elif item.annotation is not None:
                observation_item = DatabaseAnnotation.get(item.annotation)
            else:
                raise ValueError("Observation must have an item to observe.")
            database_item = DatabaseObservation(
                project,
                schema,
                item.identifier,
                observation_item,
                uid=item.uid,
                commit=False,
            )
        else:
            raise TypeError(f"Unknown item type {item}.")
        self._attribute_service.create_for_item(
            database_item, item.attributes, commit=False
        )
        self._validation_service.validate_item_relations(database_item)
        self._mapper_service.apply_mappers_to_item(database_item, commit=False)
        if commit:
            db.session.commit()
        return database_item  # type: ignore

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
        project = self._database_service.get_project(project_uid)
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
            items = self._database_service.get_project_samples(
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
        elif isinstance(item_schema, DatabaseImageSchema):
            items = self._database_service.get_project_images(
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
        elif isinstance(item_schema, DatabaseAnnotationSchema):
            items = self._database_service.get_project_annotations(
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
        elif isinstance(item_schema, DatabaseObservationSchema):
            items = self._database_service.get_project_observations(
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
        else:
            raise TypeError(f"Unknown item type {item_schema}.")

        return (item.model for item in items)

    def get_count_for_schema(
        self,
        item_schema_uid: UUID,
        project_uid: UUID,
        identifier_filter: Optional[str] = None,
        attribute_filters: Optional[Dict[str, str]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> int:
        return self._database_service.get_project_item_count(
            project_uid,
            item_schema_uid,
            identifier_filter,
            attribute_filters,
            selected=selected,
            valid=valid,
        )

    def get_or_add_image(
        self,
        identifier: str,
        schema: DatabaseImageSchema,
        samples: Sequence["DatabaseSample"],
        attributes: Optional[Dict[str, DatabaseAttribute]] = None,
        name: Optional[str] = None,
        pseudonym: Optional[str] = None,
        external_identifier: Optional[str] = None,
        commit: bool = True,
    ) -> "DatabaseImage":
        # Check if any of the samples already have the image
        image = next(
            (
                sample
                for sample in (
                    self._database_service.get_image_in_sample(sample, identifier)
                    for sample in samples
                )
                if sample is not None
            ),
            None,
        )

        if image is not None:
            # Add all samples to image
            image.set_samples(samples, commit=commit)
        else:
            # Create a new image
            image = DatabaseImage(
                project=samples[0].project,
                schema=schema,
                identifier=identifier,
                attributes=attributes,
                samples=samples,
                name=name,
                pseudonym=pseudonym,
                external_identifier=external_identifier,
                commit=commit,
            )
        return image

    def get_or_add_child(
        self,
        identifier: str,
        schema: Union[UUID, DatabaseSampleSchema],
        parents: Sequence["DatabaseSample"],
        attributes: Optional[Dict[str, DatabaseAttribute]] = None,
        name: Optional[str] = None,
        pseudonym: Optional[str] = None,
        commit: bool = True,
    ) -> "DatabaseSample":
        # Check if any of the parents already have the child
        child = next(
            (
                child
                for child in (
                    self._database_service.get_sample_child(parent, identifier, schema)
                    for parent in parents
                )
                if child is not None
            ),
            None,
        )

        if child is not None:
            # Add all parents to child
            child.set_parents(parents, commit=False)
        else:
            if not isinstance(schema, DatabaseSampleSchema):
                child_type_schema = DatabaseSampleSchema.get(schema)
                if child_type_schema is None:
                    raise ValueError(f"Sample schema with uid {schema} not found.")
                schema = child_type_schema
            # Create a new child
            child = DatabaseSample(
                project=parents[0].project,
                name=name,
                schema=schema,
                parents=parents,
                attributes=attributes,
                identifier=identifier,
                pseudonym=pseudonym,
                commit=commit,
            )
        return child
