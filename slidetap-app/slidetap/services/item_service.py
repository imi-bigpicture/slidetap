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

import uuid
from typing import Dict, Iterable, Optional, Union
from uuid import UUID

from flask import current_app
from slidetap.database import (
    DatabaseAnnotation,
    DatabaseBatch,
    DatabaseDataset,
    DatabaseImage,
    DatabaseItem,
    DatabaseObservation,
    DatabaseSample,
    db,
)
from slidetap.model import (
    Annotation,
    AnnotationSchema,
    ColumnSort,
    Image,
    ImageSchema,
    ImageStatus,
    Item,
    ItemSchema,
    ItemType,
    Observation,
    ObservationSchema,
    Sample,
    SampleSchema,
)
from slidetap.model.batch import Batch
from slidetap.model.dataset import Dataset
from slidetap.model.item_reference import ItemReference
from slidetap.services.attribute_service import AttributeService
from slidetap.services.database_service import DatabaseService
from slidetap.services.mapper_service import MapperService
from slidetap.services.schema_service import SchemaService
from slidetap.services.validation_service import ValidationService


class ItemService:
    """Item service should be used to interface with items"""

    def __init__(
        self,
        attribute_service: AttributeService,
        mapper_service: MapperService,
        schema_service: SchemaService,
        validation_service: ValidationService,
        database_service: DatabaseService,
    ) -> None:
        self._attribute_service = attribute_service
        self._mapper_service = mapper_service
        self._schema_service = schema_service
        self._validation_service = validation_service
        self._database_service = database_service

    def get(self, item_uid: UUID) -> Optional[Item]:
        item = self._database_service.get_item(item_uid)
        if item is None:
            return None
        return item.model

    def get_sample(self, item_uid: UUID) -> Optional[Sample]:
        item = self._database_service.get_sample(item_uid)
        if item is None:
            return None
        return item.model

    def get_image(self, item_uid: UUID) -> Optional[Image]:
        item = self._database_service.get_image(item_uid)
        if item is None:
            return None
        return item.model

    def get_annotation(self, item_uid: UUID) -> Optional[Annotation]:
        item = self._database_service.get_annotation(item_uid)
        if item is None:
            return None
        return item.model

    def get_observation(self, item_uid: UUID) -> Optional[Observation]:
        item = self._database_service.get_observation(item_uid)
        if item is None:
            return None
        return item.model

    def select(self, item_uid: UUID, value: bool) -> Optional[Item]:
        item = self._database_service.get_item(item_uid)
        if item is None:
            return None
        self.select_item(item, value)
        self._validation_service.validate_item_relations(item)
        db.session.commit()
        return item.model

    def update(self, item: Item) -> Optional[Item]:
        existing_item = self._database_service.get_optional_item(item.uid)
        if existing_item is None:
            return None
        existing_item.name = item.name
        existing_item.identifier = item.identifier
        if isinstance(existing_item, DatabaseSample):
            if not isinstance(item, Sample):
                raise TypeError(f"Expected Sample, got {type(item)}.")
            existing_item.parents = [
                self._database_service.get_sample(parent) for parent in item.parents
            ]
            existing_item.children = [
                self._database_service.get_sample(child) for child in item.children
            ]
            existing_item.images = [
                self._database_service.get_image(image) for image in item.images
            ]
            existing_item.observations = [
                self._database_service.get_observation(observation)
                for observation in item.observations
            ]
        elif isinstance(existing_item, DatabaseImage):
            if not isinstance(item, Image):
                raise TypeError(f"Expected Image, got {type(item)}.")
            existing_item.samples = [
                self._database_service.get_sample(sample) for sample in item.samples
            ]

        elif isinstance(existing_item, DatabaseAnnotation):
            if not isinstance(item, Annotation):
                raise TypeError(f"Expected Annotation, got {type(item)}.")
            existing_item.image = (
                self._database_service.get_image(item.image)
                if item.image is not None
                else None
            )
        elif isinstance(existing_item, DatabaseObservation):
            if not isinstance(item, Observation):
                raise TypeError(f"Expected Observation, got {type(item)}.")
            if item.sample is not None:
                existing_item.sample = self._database_service.get_sample(item.sample)
            elif item.image is not None:
                existing_item.image = self._database_service.get_image(item.image)
            elif item.annotation is not None:
                existing_item.annotation = self._database_service.get_annotation(
                    item.annotation
                )
        else:
            raise TypeError(f"Unknown item type {existing_item}.")
        self._attribute_service.update_for_item(existing_item, item.attributes)
        self._validation_service.validate_item_relations(existing_item)

    def add_and_return_model(self, item: ItemType) -> ItemType:
        return self.add(item).model

    def add(self, item: ItemType, commit: bool = True) -> DatabaseItem[ItemType]:
        existing_item = self._database_service.get_optional_item(item.uid)
        if existing_item is not None:
            current_app.logger.info(f"Item {item.uid, item.identifier} already exists.")
            return existing_item
        database_item = self._database_service.add_item(item, commit=commit)
        self._attribute_service.create_for_item(
            database_item, item.attributes, commit=False
        )
        self._mapper_service.apply_mappers_to_item(
            database_item, commit=False, validate=True
        )
        self._validation_service.validate_item_attributes(database_item)
        self._validation_service.validate_item_relations(database_item)
        if commit:
            db.session.commit()
        return database_item  # type: ignore

    def create(
        self,
        item_schema: Union[UUID, ItemSchema],
        dataset: Union[UUID, Dataset, DatabaseDataset],
        batch: Union[UUID, Batch, DatabaseBatch],
    ) -> Optional[Item]:
        if isinstance(item_schema, UUID):
            item_schema = self._schema_service.items[item_schema]
        if isinstance(dataset, (Dataset, DatabaseDataset)):
            dataset = dataset.uid
        if isinstance(batch, (Batch, DatabaseBatch)):
            batch = batch.uid
        if isinstance(item_schema, SampleSchema):
            sample = Sample(
                uid=uuid.UUID(int=0),
                identifier="New sample",
                dataset_uid=dataset,
                schema_uid=item_schema.uid,
                batch_uid=batch,
            )
            return self._database_service.add_item(sample).model

        if isinstance(item_schema, ImageSchema):
            image = Image(
                uid=uuid.UUID(int=0),
                identifier="New image",
                dataset_uid=dataset,
                schema_uid=item_schema.uid,
                batch_uid=batch,
            )
            return self._database_service.add_item(image).model
        if isinstance(item_schema, AnnotationSchema):
            annotation = Annotation(
                uid=uuid.UUID(int=0),
                identifier="New annotation",
                dataset_uid=dataset,
                schema_uid=item_schema.uid,
                batch_uid=batch,
            )
            return self._database_service.add_item(annotation).model
        if isinstance(item_schema, ObservationSchema):
            observation = Observation(
                uid=uuid.UUID(int=0),
                identifier="New observation",
                dataset_uid=dataset,
                schema_uid=item_schema.uid,
                batch_uid=batch,
            )
            return self._database_service.add_item(observation).model

        raise TypeError(f"Unknown item schema {item_schema}.")

    def get_for_schema(
        self,
        item_schema_uid: UUID,
        dataset_uid: UUID,
        batch_uid: Optional[UUID] = None,
        start: Optional[int] = None,
        size: Optional[int] = None,
        identifier_filter: Optional[str] = None,
        attribute_filters: Optional[Dict[str, str]] = None,
        sorting: Optional[Iterable[ColumnSort]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
        status_filter: Optional[Iterable[ImageStatus]] = None,
    ) -> Iterable[Item]:
        items = self._get_for_schema(
            item_schema_uid,
            dataset_uid,
            batch_uid,
            start,
            size,
            identifier_filter,
            attribute_filters,
            sorting,
            selected,
            valid,
            status_filter,
        )

        return (item.model for item in items)

    def get_references_for_schema(
        self,
        item_schema_uid: UUID,
        dataset_uid: UUID,
        batch_uid: Optional[UUID] = None,
        start: Optional[int] = None,
        size: Optional[int] = None,
        identifier_filter: Optional[str] = None,
        attribute_filters: Optional[Dict[str, str]] = None,
        sorting: Optional[Iterable[ColumnSort]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
        status_filter: Optional[Iterable[ImageStatus]] = None,
    ) -> Iterable[ItemReference]:
        items = self._get_for_schema(
            item_schema_uid,
            dataset_uid,
            batch_uid,
            start,
            size,
            identifier_filter,
            attribute_filters,
            sorting,
            selected,
            valid,
            status_filter,
        )

        return (item.reference for item in items)

    def get_count_for_schema(
        self,
        item_schema_uid: UUID,
        dataset_uid: UUID,
        batch_uid: Optional[UUID] = None,
        identifier_filter: Optional[str] = None,
        attribute_filters: Optional[Dict[str, str]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
        status_filter: Optional[Iterable[ImageStatus]] = None,
    ) -> int:
        return self._database_service.get_item_count(
            dataset_uid,
            batch_uid,
            item_schema_uid,
            identifier_filter,
            attribute_filters,
            selected=selected,
            valid=valid,
            status_filter=status_filter,
        )

    def select_item(self, item: Union[UUID, Item, DatabaseItem], value: bool):
        if isinstance(item, UUID):
            item = self._database_service.get_item(item)
        if isinstance(item, (Sample, DatabaseSample)):
            return self.select_sample(item, value)
        if isinstance(item, (Image, DatabaseImage)):
            return self.select_image(item, value)
        if isinstance(item, (Annotation, DatabaseAnnotation)):
            raise NotImplementedError()
        if isinstance(item, (Observation, DatabaseObservation)):
            return self.select_observation(item, value)

    def select_image(self, image: Union[UUID, Image, DatabaseImage], value: bool):
        """Select or deselect an image.

        If the image is selected, all samples are also selected.
        If the image is deselected, observations and annotations are also deselected."""
        image = self._database_service.get_image(image)
        image.selected = value
        if value:
            for sample in image.samples:
                self.select_sample(sample, True)
        else:
            for observation in image.observations:
                observation.selected = False
            for annotation in image.annotations:
                annotation.selected = False

    def select_sample(self, sample: Union[UUID, Sample, DatabaseSample], value: bool):
        """Select or deselect a sample.

        Recursively selects or deselects all children and parents of the sample.
        If the sample is deselected, all observations and images are also deselected.
        """
        sample = self._database_service.get_sample(sample)
        sample.selected = value
        for child in sample.children:
            self._select_sample_from_parent(child, value)
        for parent in sample.parents:
            self._select_sample_from_child(parent, value)
        if not value:
            for observation in sample.observations:
                observation.selected = False
            for image in sample.images:
                image.selected = False

    def select_observation(
        self, observation: Union[UUID, Observation, DatabaseObservation], value: bool
    ):
        """Select or deselect an observation.

        If the observation is selected, the item it observes is also selected.
        """
        observation = self._database_service.get_observation(observation)
        observation.selected = value
        if value:
            self.select_item(observation.item, True)

    def select_annotation(
        self, annotation: Union[UUID, Annotation, DatabaseAnnotation], value: bool
    ):
        """Select or deselect an annotation.

        If the annotation is selected, the image it is attached to is also selected.
        """
        annotation = self._database_service.get_annotation(annotation)
        annotation.selected = value
        if value and annotation.image is not None:
            self.select_item(annotation.image, True)

    def copy(self, item: Union[UUID, Item, DatabaseItem]) -> Item:
        if isinstance(item, (UUID, Item)):
            item = self._database_service.get_item(item)
        if isinstance(item, DatabaseObservation):
            return DatabaseObservation(
                item.dataset_uid,
                schema_uid=item.schema_uid,
                identifier=f"{item.identifier} (copy)",
                batch_uid=item.batch_uid,
                item=item.item,
                attributes={
                    attribute.tag: attribute.copy()
                    for attribute in item.attributes.values()
                },
                name=f"{item.name} (copy)" if item.name else None,
                pseudonym=f"{item.pseudonym} (copy)" if item.pseudonym else None,
                add=False,
                commit=False,
            ).model
        if isinstance(item, DatabaseAnnotation):
            return DatabaseAnnotation(
                item.dataset_uid,
                schema_uid=item.schema_uid,
                identifier=f"{item.identifier} (copy)",
                batch_uid=item.batch_uid,
                image=item.image,
                attributes={
                    attribute.tag: attribute.copy()
                    for attribute in item.attributes.values()
                },
                name=f"{item.name} (copy)" if item.name else None,
                pseudonym=f"{item.pseudonym} (copy)" if item.pseudonym else None,
                add=False,
                commit=False,
            ).model
        if isinstance(item, DatabaseImage):
            return DatabaseImage(
                item.dataset_uid,
                schema_uid=item.schema_uid,
                identifier=f"{item.identifier} (copy)",
                batch_uid=item.batch_uid,
                samples=item.samples,
                attributes={
                    attribute.tag: attribute.copy()
                    for attribute in item.attributes.values()
                },
                name=f"{item.name} (copy)" if item.name else None,
                pseudonym=f"{item.pseudonym} (copy)" if item.pseudonym else None,
                add=False,
                commit=False,
            ).model
        if isinstance(item, DatabaseSample):
            return DatabaseSample(
                item.dataset_uid,
                identifier=f"{item.identifier} (copy)",
                batch_uid=item.batch_uid,
                schema_uid=item.schema_uid,
                parents=item.parents,
                attributes={
                    attribute.tag: attribute.copy()
                    for attribute in item.attributes.values()
                },
                name=f"{item.name} (copy)" if item.name else None,
                pseudonym=f"{item.pseudonym} (copy)" if item.pseudonym else None,
                add=False,
                commit=False,
            ).model
        raise TypeError(f"Unknown item type {item}.")

    def _select_sample_from_parent(self, child: DatabaseSample, parent_selected: bool):
        """Select or deselect a child based on the selection of one parent.

        If all parents are selected, the child is selected.
        If the parent is deselected, the child is deselected.
        Recurse the child selection to all children, images, and observations."""
        if parent_selected:
            if all(parent.selected for parent in child.parents):
                child.selected = True
        else:
            child.selected = False
        for child_child in child.children:
            self._select_sample_from_parent(child_child, child.selected)
        for image in child.images:
            self._select_image_from_sample(image, child.selected)
        for observation in child.observations:
            observation.selected = child.selected

    def _select_sample_from_child(
        self,
        parent: DatabaseSample,
        child_selected: bool,
    ):
        """Select or deselect a parent based on the selection of one child.

        If one child is selected, the parent is selected.
        If all children are deselected, the parent is deselected.
        Recurse the parent selection to all parents, images, and observations.

        """
        if child_selected:
            parent.selected = True
        elif all(not child.selected for child in parent.children):
            parent.selected = False
        for parent_parent in parent.parents:
            self._select_sample_from_child(parent_parent, child_selected)
        for image in parent.images:
            self._select_image_from_sample(image, child_selected)
        for observation in parent.observations:
            observation.selected = child_selected

    def _select_image_from_sample(self, image: DatabaseImage, sample_selection: bool):
        """Select or deselect an image based on the selection of one sample.

        If the sample is deselected, the image and its annotations and observations are
        deselected.
        If all samples are selected, the image is selected.
        """
        if not sample_selection:
            image.selected = False
            for annotation in image.annotations:
                annotation.selected = False
            for observation in image.observations:
                observation.selected = False
        elif all(sample.selected for sample in image.samples):
            image.selected = True

    def _get_for_schema(
        self,
        item_schema_uid: UUID,
        dataset_uid: Optional[UUID] = None,
        batch_uid: Optional[UUID] = None,
        start: Optional[int] = None,
        size: Optional[int] = None,
        identifier_filter: Optional[str] = None,
        attribute_filters: Optional[Dict[str, str]] = None,
        sorting: Optional[Iterable[ColumnSort]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
        status_filter: Optional[Iterable[ImageStatus]] = None,
    ) -> Iterable[DatabaseItem]:
        item_schema = self._schema_service.items[item_schema_uid]
        if isinstance(item_schema, SampleSchema):
            items = self._database_service.get_samples(
                dataset_uid,
                batch_uid,
                item_schema,
                start,
                size,
                identifier_filter,
                attribute_filters,
                sorting,
                selected,
                valid,
            )
        elif isinstance(item_schema, ImageSchema):
            items = self._database_service.get_images(
                dataset_uid,
                batch_uid,
                item_schema,
                start,
                size,
                identifier_filter,
                attribute_filters,
                sorting,
                selected,
                valid,
                status_filter,
            )
        elif isinstance(item_schema, AnnotationSchema):
            items = self._database_service.get_annotations(
                dataset_uid,
                batch_uid,
                item_schema,
                start,
                size,
                identifier_filter,
                attribute_filters,
                sorting,
                selected,
                valid,
            )
        elif isinstance(item_schema, ObservationSchema):
            items = self._database_service.get_observations(
                dataset_uid,
                batch_uid,
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

        return items
