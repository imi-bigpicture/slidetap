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

from typing import Dict, Iterable, Optional, Union
from uuid import UUID

from slidetap.database import (
    DatabaseAnnotation,
    DatabaseImage,
    DatabaseItem,
    DatabaseItemType,
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
    Item,
    ItemSchema,
    ItemType,
    Observation,
    ObservationSchema,
    Sample,
    SampleSchema,
)
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
        item = DatabaseItem.get_optional(item_uid)
        if item is None:
            return None
        return item.model

    def select(self, item_uid: UUID, value: bool) -> Optional[Item]:
        item = DatabaseItem.get_optional(item_uid)
        if item is None:
            return None
        self.select_item(item, value)
        self._validation_service.validate_item_relations(item)
        return item.model

    def get_schema_for_item(self, item_uid: UUID) -> Optional[ItemSchema]:
        item = DatabaseItem.get_optional(item_uid)
        return
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
            existing_item.parents = [
                DatabaseSample.get(parent) for parent in item.parents
            ]
            existing_item.children = [
                DatabaseSample.get(child) for child in item.children
            ]
            existing_item.images = [DatabaseImage.get(image) for image in item.images]
            existing_item.observations = [
                DatabaseObservation.get(observation)
                for observation in item.observations
            ]
        elif isinstance(existing_item, DatabaseImage):
            if not isinstance(item, Image):
                raise TypeError(f"Expected Image, got {type(item)}.")
            existing_item.samples = [
                DatabaseSample.get(sample) for sample in item.samples
            ]

        elif isinstance(existing_item, DatabaseAnnotation):
            if not isinstance(item, Annotation):
                raise TypeError(f"Expected Annotation, got {type(item)}.")
            existing_item.image = DatabaseImage.get(item.image) if item.image else None
        elif isinstance(existing_item, DatabaseObservation):
            if not isinstance(item, Observation):
                raise TypeError(f"Expected Observation, got {type(item)}.")
            if item.sample is not None:
                existing_item.sample = DatabaseSample.get(item.sample)
            elif item.image is not None:
                existing_item.image = DatabaseImage.get(item.image)
            elif item.annotation is not None:
                existing_item.annotation = DatabaseAnnotation.get(item.annotation)
        else:
            raise TypeError(f"Unknown item type {existing_item}.")
        self._attribute_service.update_for_item(existing_item, item.attributes)
        self._validation_service.validate_item_relations(existing_item)

    def add_and_return_model(self, item: ItemType) -> ItemType:
        return self.add(item).model

    def add(self, item: ItemType, commit: bool = True) -> DatabaseItem[ItemType]:
        if isinstance(item, Sample):
            database_item = DatabaseSample(
                item.project_uid,
                item.schema_uid,
                item.identifier,
                parents=[DatabaseSample.get(parent) for parent in item.parents],
                children=[DatabaseSample.get(child) for child in item.children],
                uid=item.uid,
                commit=False,
            )
        elif isinstance(item, Image):
            database_item = DatabaseImage(
                item.project_uid,
                item.schema_uid,
                item.identifier,
                samples=[DatabaseSample.get(sample) for sample in item.samples],
                uid=item.uid,
                commit=False,
            )
        elif isinstance(item, Annotation):
            database_item = DatabaseAnnotation(
                item.project_uid,
                item.schema_uid,
                item.identifier,
                image=DatabaseImage.get(item.image) if item.image else None,
                uid=item.uid,
                commit=False,
            )
        elif isinstance(item, Observation):
            if item.sample is not None:
                observation_item = DatabaseSample.get(item.sample)
            elif item.image is not None:
                observation_item = DatabaseImage.get(item.image)
            elif item.annotation is not None:
                observation_item = DatabaseAnnotation.get(item.annotation)
            else:
                raise ValueError("Observation must have an item to observe.")
            database_item = DatabaseObservation(
                item.project_uid,
                item.schema_uid,
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

    def create(
        self, item_schema: Union[UUID, ItemSchema], project_uid: UUID
    ) -> Optional[Item]:
        if isinstance(item_schema, UUID):
            item_schema = self._schema_service.items[item_schema]

        if isinstance(item_schema, SampleSchema):
            return DatabaseSample(
                project_uid,
                item_schema.uid,
                "New sample",
                [],
                [],
                add=False,
                commit=False,
            ).model
        if isinstance(item_schema, ImageSchema):
            return DatabaseImage(
                project_uid,
                item_schema.uid,
                "New image",
                [],
                add=False,
                commit=False,
            ).model
        if isinstance(item_schema, AnnotationSchema):
            return DatabaseAnnotation(
                project_uid,
                item_schema.uid,
                "New annotation",
                None,
                add=False,
                commit=False,
            ).model
        if isinstance(item_schema, ObservationSchema):
            return DatabaseObservation(
                project_uid,
                item_schema.uid,
                "New observation",
                None,
                add=False,
                commit=False,
            ).model
        raise TypeError(f"Unknown item schema {item_schema}.")

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
        item_schema = self._schema_service.items[item_schema_uid]
        if isinstance(item_schema, SampleSchema):
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
        elif isinstance(item_schema, ImageSchema):
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
        elif isinstance(item_schema, AnnotationSchema):
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
        elif isinstance(item_schema, ObservationSchema):
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
                project_uid=item.project_uid,
                schema_uid=item.schema_uid,
                identifier=f"{item.identifier} (copy)",
                item=item.item,
                attributes={
                    attribute.tag: attribute.copy()
                    for attribute in item.iterate_attributes()
                },
                name=f"{item.name} (copy)" if item.name else None,
                pseudonym=f"{item.pseudonym} (copy)" if item.pseudonym else None,
                add=False,
                commit=False,
            ).model
        if isinstance(item, DatabaseAnnotation):
            return DatabaseAnnotation(
                project_uid=item.project_uid,
                schema_uid=item.schema_uid,
                identifier=f"{item.identifier} (copy)",
                image=item.image,
                attributes={
                    attribute.tag: attribute.copy()
                    for attribute in item.iterate_attributes()
                },
                name=f"{item.name} (copy)" if item.name else None,
                pseudonym=f"{item.pseudonym} (copy)" if item.pseudonym else None,
                add=False,
                commit=False,
            ).model
        if isinstance(item, DatabaseImage):
            return DatabaseImage(
                project_uid=item.project_uid,
                schema_uid=item.schema_uid,
                identifier=f"{item.identifier} (copy)",
                samples=item.samples,
                attributes={
                    attribute.tag: attribute.copy()
                    for attribute in item.iterate_attributes()
                },
                name=f"{item.name} (copy)" if item.name else None,
                pseudonym=f"{item.pseudonym} (copy)" if item.pseudonym else None,
                add=False,
                commit=False,
            ).model
        if isinstance(item, DatabaseSample):
            return DatabaseSample(
                project_uid=item.project_uid,
                identifier=f"{item.identifier} (copy)",
                schema_uid=item.schema_uid,
                parents=item.parents,
                attributes={
                    attribute.tag: attribute.copy()
                    for attribute in item.iterate_attributes()
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
                self.selected = True
        else:
            self.selected = False
        for child in child.children:
            self._select_sample_from_parent(child, self.selected)
        for image in child.images:
            self._select_image_from_sample(image, self.selected)
        for observation in child.observations:
            observation.selected = self.selected

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
            self.selected = True
        elif all(not child.selected for child in parent.children):
            self.selected = False
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
