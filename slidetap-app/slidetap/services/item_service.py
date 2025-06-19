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

import logging
import uuid
from typing import Dict, Iterable, List, Optional, Union
from uuid import UUID

from sqlalchemy.orm import Session

from slidetap.database import (
    DatabaseAnnotation,
    DatabaseBatch,
    DatabaseDataset,
    DatabaseImage,
    DatabaseItem,
    DatabaseObservation,
    DatabaseSample,
)
from slidetap.model import (
    Annotation,
    AnnotationSchema,
    Batch,
    ColumnSort,
    Dataset,
    Image,
    ImageSchema,
    ImageStatus,
    Item,
    ItemReference,
    ItemSchema,
    ItemType,
    Observation,
    ObservationSchema,
    Sample,
    SampleSchema,
)
from slidetap.model.item import AnyItem, ImageGroup
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

    def get(self, item_uid: UUID) -> Optional[AnyItem]:
        with self._database_service.get_session() as session:
            item = self._database_service.get_item(session, item_uid)
            if item is None:
                return None
            return item.model

    def get_sample(self, item_uid: UUID) -> Optional[Sample]:
        with self._database_service.get_session() as session:
            item = self._database_service.get_sample(session, item_uid)
            if item is None:
                return None
            return item.model

    def get_image(self, item_uid: UUID) -> Optional[Image]:
        with self._database_service.get_session() as session:
            item = self._database_service.get_image(session, item_uid)
            if item is None:
                return None
            return item.model

    def get_annotation(self, item_uid: UUID) -> Optional[Annotation]:
        with self._database_service.get_session() as session:
            item = self._database_service.get_annotation(session, item_uid)
            if item is None:
                return None
            return item.model

    def get_observation(self, item_uid: UUID) -> Optional[Observation]:
        with self._database_service.get_session() as session:
            item = self._database_service.get_observation(session, item_uid)
            if item is None:
                return None
            return item.model

    def get_images_for_item(
        self,
        item_uid: UUID,
        group_by_schema_uid: UUID,
        image_schema_uid: Optional[UUID] = None,
    ) -> List[ImageGroup]:
        group_by_schema = self._schema_service.get_item(group_by_schema_uid)
        with self._database_service.get_session() as session:
            item = self._database_service.get_item(
                session,
                item_uid,
            )
            if isinstance(item, DatabaseSample):
                if group_by_schema_uid == item.schema_uid:
                    return [
                        ImageGroup(
                            identifier=item.identifier,
                            name=item.name,
                            schema_uid=item.schema_uid,
                            images=[
                                image.model
                                for image in self._database_service.get_sample_images(
                                    session, item, image_schema_uid, recursive=True
                                )
                            ],
                        )
                    ]
                if isinstance(group_by_schema, SampleSchema):
                    groups = self._database_service.get_sample_children(
                        session, item, group_by_schema_uid, recursive=True
                    )
                    return [
                        ImageGroup(
                            identifier=group.identifier,
                            name=group.name,
                            schema_uid=group.schema_uid,
                            images=[
                                image.model
                                for image in self._database_service.get_sample_images(
                                    session, group, image_schema_uid, recursive=True
                                )
                            ],
                        )
                        for group in groups
                    ]
                if isinstance(group_by_schema, ImageSchema):
                    images = self._database_service.get_sample_images(
                        session, item, group_by_schema_uid, recursive=True
                    )
                    return [
                        ImageGroup(
                            identifier=image.identifier,
                            name=image.name,
                            schema_uid=image.schema_uid,
                            images=[image.model],
                        )
                        for image in images
                    ]

            if isinstance(item, DatabaseImage):
                if not group_by_schema_uid == item.schema_uid:
                    raise TypeError(
                        f"Cannot group by {group_by_schema} for image {item_uid}."
                    )
                return [
                    ImageGroup(
                        identifier=item.identifier,
                        name=item.name,
                        schema_uid=item.schema_uid,
                        images=[item.model],
                    )
                ]
            if isinstance(item, DatabaseAnnotation):
                if group_by_schema_uid == item.schema_uid:
                    return [
                        ImageGroup(
                            identifier=item.identifier,
                            name=item.name,
                            schema_uid=item.schema_uid,
                            images=(
                                [item.image.model]
                                if item.image
                                and (
                                    image_schema_uid is None
                                    or item.image.schema_uid == image_schema_uid
                                )
                                else []
                            ),
                        )
                    ]
                if isinstance(group_by_schema, ImageSchema):
                    if item.image is None or (
                        image_schema_uid is not None
                        and item.image.schema_uid != image_schema_uid
                    ):
                        return []
                    return [
                        ImageGroup(
                            identifier=item.image.identifier,
                            name=item.image.name,
                            schema_uid=item.image.schema_uid,
                            images=[item.image.model],
                        )
                    ]
            if isinstance(item, DatabaseObservation):
                if group_by_schema_uid == item.schema_uid:
                    return [
                        ImageGroup(
                            identifier=item.identifier,
                            name=item.name,
                            schema_uid=item.schema_uid,
                            images=[
                                image.model
                                for image in self._database_service.get_observation_images(
                                    session, item, image_schema_uid, recursive=True
                                )
                            ],
                        )
                    ]
                if isinstance(group_by_schema, ImageSchema):
                    if item.image is None or (
                        image_schema_uid is not None
                        and item.image.schema_uid != image_schema_uid
                    ):
                        return []
                    return [
                        ImageGroup(
                            identifier=item.image.identifier,
                            name=item.image.name,
                            schema_uid=item.image.schema_uid,
                            images=[item.image.model],
                        )
                    ]
                if isinstance(group_by_schema, SampleSchema):
                    groups = self._database_service.get_observation_samples(
                        session, item, group_by_schema_uid, recursive=True
                    )
                    return [
                        ImageGroup(
                            identifier=group.identifier,
                            name=group.name,
                            schema_uid=group.schema_uid,
                            images=[
                                image.model
                                for image in self._database_service.get_sample_images(
                                    session, group, image_schema_uid, recursive=True
                                )
                            ],
                        )
                        for group in groups
                    ]
                if isinstance(group_by_schema, AnnotationSchema):
                    if (
                        item.annotation is None
                        or item.annotation.image is None
                        or (
                            image_schema_uid is not None
                            and item.annotation.image.schema_uid != image_schema_uid
                        )
                    ):
                        return []
                    return [
                        ImageGroup(
                            identifier=item.annotation.image.identifier,
                            name=item.annotation.image.name,
                            schema_uid=item.annotation.image.schema_uid,
                            images=[item.annotation.image.model],
                        )
                    ]

            raise ValueError(
                f"Cannot get images for item {item_uid} with schema {group_by_schema_uid}."
            )

    def select(self, item_uid: UUID, value: bool) -> Optional[Item]:
        with self._database_service.get_session() as session:
            item = self._database_service.get_item(session, item_uid)
            if item is None:
                return None
            self.select_item(item, value)
            self._validation_service.validate_item_relations(item, session)
            return item.model

    def update(self, item: AnyItem) -> Optional[Item]:
        with self._database_service.get_session() as session:
            existing_item = self._database_service.get_optional_item(session, item.uid)
            if existing_item is None:
                return None
            existing_item.name = item.name
            existing_item.identifier = item.identifier
            if isinstance(existing_item, DatabaseSample):
                if not isinstance(item, Sample):
                    raise TypeError(f"Expected Sample, got {type(item)}.")
                existing_item.parents = [
                    self._database_service.get_sample(session, parent)
                    for parent in item.parents
                ]
                existing_item.children = [
                    self._database_service.get_sample(session, child)
                    for child in item.children
                ]
                existing_item.images = [
                    self._database_service.get_image(session, image)
                    for image in item.images
                ]
                existing_item.observations = [
                    self._database_service.get_observation(session, observation)
                    for observation in item.observations
                ]
            elif isinstance(existing_item, DatabaseImage):
                if not isinstance(item, Image):
                    raise TypeError(f"Expected Image, got {type(item)}.")
                existing_item.samples = [
                    self._database_service.get_sample(session, sample)
                    for sample in item.samples
                ]

            elif isinstance(existing_item, DatabaseAnnotation):
                if not isinstance(item, Annotation):
                    raise TypeError(f"Expected Annotation, got {type(item)}.")
                existing_item.image = (
                    self._database_service.get_image(session, item.image)
                    if item.image is not None
                    else None
                )
            elif isinstance(existing_item, DatabaseObservation):
                if not isinstance(item, Observation):
                    raise TypeError(f"Expected Observation, got {type(item)}.")
                if item.sample is not None:
                    existing_item.sample = self._database_service.get_sample(
                        session, item.sample
                    )
                elif item.image is not None:
                    existing_item.image = self._database_service.get_image(
                        session, item.image
                    )
                elif item.annotation is not None:
                    existing_item.annotation = self._database_service.get_annotation(
                        session, item.annotation
                    )
            else:
                raise TypeError(f"Unknown item type {existing_item}.")
            self._attribute_service.update_for_item(
                existing_item, item.attributes, session=session
            )
            self._validation_service.validate_item_relations(existing_item, session)
            return existing_item.model

    def add(
        self, item: AnyItem, map: bool = True, session: Optional[Session] = None
    ) -> AnyItem:
        with self._database_service.get_session(session) as session:
            existing_item = self._database_service.get_optional_item_by_identifier(
                session, item.identifier, item.schema_uid, item.dataset_uid
            )
            if existing_item is not None:
                logging.info(f"Item {item.uid, item.identifier} already exists.")
                return existing_item.model
            schema = self._schema_service.get_item(item.schema_uid)
            database_item = self._database_service.add_item(
                session,
                item,
                schema,
            )
            database_item.attributes = (
                self._attribute_service.create_or_update_attributes(
                    item.attributes, session=session
                )
            )
            database_item.private_attributes = (
                self._attribute_service.create_or_update_attributes(
                    item.private_attributes, session=session
                )
            )
            if map:
                batch = self._database_service.get_batch(
                    session, database_item.batch_uid
                )
                project_mappers = [
                    mapper
                    for group in batch.project.mapper_groups
                    for mapper in group.mappers
                ]
                self._mapper_service.apply_mappers_to_attributes(
                    database_item.attributes,
                    project_mappers,
                    validate=False,
                    session=session,
                )
            self._validation_service.validate_item_attributes(database_item, session)
            self._validation_service.validate_item_relations(database_item, session)
            return database_item.model  # type: ignore

    def create(
        self,
        item_schema: Union[UUID, ItemSchema],
        dataset: Union[UUID, Dataset, DatabaseDataset],
        batch: Union[UUID, Batch, DatabaseBatch],
    ) -> Optional[AnyItem]:
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
            return self.add(sample)
        if isinstance(item_schema, ImageSchema):
            image = Image(
                uid=uuid.UUID(int=0),
                identifier="New image",
                dataset_uid=dataset,
                schema_uid=item_schema.uid,
                batch_uid=batch,
            )
            return self.add(image)
        if isinstance(item_schema, AnnotationSchema):
            annotation = Annotation(
                uid=uuid.UUID(int=0),
                identifier="New annotation",
                dataset_uid=dataset,
                schema_uid=item_schema.uid,
                batch_uid=batch,
            )
            return self.add(annotation)
        if isinstance(item_schema, ObservationSchema):
            observation = Observation(
                uid=uuid.UUID(int=0),
                identifier="New observation",
                dataset_uid=dataset,
                schema_uid=item_schema.uid,
                batch_uid=batch,
            )
            return self.add(observation)

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
    ) -> Iterable[AnyItem]:
        with self._database_service.get_session() as session:
            items = self._get_for_schema(
                session,
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

            return [item.model for item in items]

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
        with self._database_service.get_session() as session:
            items = self._get_for_schema(
                session,
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

            return [item.reference for item in items]

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
        with self._database_service.get_session() as session:
            return self._database_service.get_item_count(
                session,
                dataset_uid,
                batch_uid,
                item_schema_uid,
                identifier_filter,
                attribute_filters,
                selected=selected,
                valid=valid,
                status_filter=status_filter,
            )

    def select_item(
        self,
        item: Union[UUID, Item, DatabaseItem],
        value: bool,
        session: Optional[Session] = None,
    ):
        with self._database_service.get_session(session) as session:
            if isinstance(item, UUID):
                item = self._database_service.get_item(session, item)
            if isinstance(item, (Sample, DatabaseSample)):
                return self.select_sample(item, value, session)
            if isinstance(item, (Image, DatabaseImage)):
                return self.select_image(item, value, session)
            if isinstance(item, (Annotation, DatabaseAnnotation)):
                return self.select_annotation(item, value, session)
            if isinstance(item, (Observation, DatabaseObservation)):
                return self.select_observation(item, value, session)

    def select_image(
        self,
        image: Union[UUID, Image, DatabaseImage],
        value: bool,
        session: Optional[Session] = None,
    ):
        """Select or deselect an image.

        If the image is selected, all samples are also selected.
        If the image is deselected, observations and annotations are also deselected."""
        with self._database_service.get_session(session) as session:
            image = self._database_service.get_image(session, image)
            image.selected = value
            if value:
                for sample in image.samples:
                    self.select_sample(sample, True, session)
            else:
                for observation in image.observations:
                    observation.selected = False
                for annotation in image.annotations:
                    annotation.selected = False

    def select_sample(
        self,
        sample: Union[UUID, Sample, DatabaseSample],
        value: bool,
        session: Optional[Session] = None,
    ):
        """Select or deselect a sample.

        Recursively selects or deselects all children and parents of the sample.
        If the sample is deselected, all observations and images are also deselected.
        """
        with self._database_service.get_session(session) as session:
            sample = self._database_service.get_sample(session, sample)
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
        self,
        observation: Union[UUID, Observation, DatabaseObservation],
        value: bool,
        session: Optional[Session] = None,
    ):
        """Select or deselect an observation.

        If the observation is selected, the item it observes is also selected.
        """
        with self._database_service.get_session(session) as session:
            observation = self._database_service.get_observation(session, observation)
            observation.selected = value
            if value:
                self.select_item(observation.item, True, session)

    def select_annotation(
        self,
        annotation: Union[UUID, Annotation, DatabaseAnnotation],
        value: bool,
        session: Optional[Session] = None,
    ):
        """Select or deselect an annotation.

        If the annotation is selected, the image it is attached to is also selected.
        """
        with self._database_service.get_session(session) as session:
            annotation = self._database_service.get_annotation(session, annotation)
            annotation.selected = value
            if value and annotation.image is not None:
                self.select_item(annotation.image, True, session)

    def copy(self, item: Union[UUID, Item, DatabaseItem]) -> AnyItem:
        with self._database_service.get_session() as session:
            copy = self._database_service.get_item(session, item).model
            copy.uid = uuid.uuid4()
            copy.identifier = f"{copy.identifier} (copy)"
            copy.name = f"{copy.name} (copy)" if copy.name else None
            copy.pseudonym = f"{copy.pseudonym} (copy)" if copy.pseudonym else None
            for attribute in copy.attributes.values():
                attribute.uid = uuid.uuid4()
            schema = self._schema_service.get_item(copy.schema_uid)
            self._database_service.add_item(session, copy, schema)
            assert isinstance(copy, (Sample, Image, Annotation, Observation))
            return copy

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
        session: Session,
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
                session,
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
                session,
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
                session,
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
                session,
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
