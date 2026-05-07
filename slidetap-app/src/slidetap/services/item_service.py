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

"""Service for accessing items."""

import logging
import uuid
from typing import Dict, Iterable, List, Optional, Sequence, Union
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
from slidetap.database.mapper import DatabaseMapper
from slidetap.external_interfaces.pseudonym_factory import PseudonymFactoryInterface
from slidetap.model import (
    Annotation,
    AnnotationSchema,
    AttributeSchema,
    Batch,
    BooleanAttribute,
    BooleanAttributeSchema,
    CodeAttribute,
    CodeAttributeSchema,
    ColumnSort,
    Dataset,
    DatetimeAttribute,
    DatetimeAttributeSchema,
    EnumAttribute,
    EnumAttributeSchema,
    Image,
    ImageFormat,
    ImageSchema,
    ImageStatus,
    Item,
    ItemReference,
    ItemSchema,
    ListAttribute,
    ListAttributeSchema,
    Mapper,
    MeasurementAttribute,
    MeasurementAttributeSchema,
    NumericAttribute,
    NumericAttributeSchema,
    ObjectAttribute,
    ObjectAttributeSchema,
    Observation,
    ObservationSchema,
    OverviewLayout,
    OverviewSectionLayout,
    Sample,
    SampleSchema,
    StringAttribute,
    StringAttributeSchema,
    UnionAttribute,
    UnionAttributeSchema,
)
from slidetap.model.attribute import AnyAttribute
from slidetap.model.item import (
    AnyItem,
    ImageGroup,
)
from slidetap.model.item_select import ItemSelect
from slidetap.model.overview import (
    OverviewItem,
    OverviewRoot,
    OverviewSection,
    RelationChange,
)
from slidetap.model.table import RelationFilter
from slidetap.services.attribute_service import AttributeService
from slidetap.services.database_service import DatabaseService
from slidetap.services.mapper_service import MapperService
from slidetap.services.schema_service import SchemaService
from slidetap.services.tag_service import TagService
from slidetap.services.validation_service import ValidationService


class ItemService:
    """Item service should be used to interface with items"""

    def __init__(
        self,
        attribute_service: AttributeService,
        tag_service: TagService,
        mapper_service: MapperService,
        schema_service: SchemaService,
        validation_service: ValidationService,
        database_service: DatabaseService,
        pseudonym_factory: Optional[PseudonymFactoryInterface] = None,
    ) -> None:
        self._attribute_service = attribute_service
        self._tag_service = tag_service
        self._mapper_service = mapper_service
        self._schema_service = schema_service
        self._validation_service = validation_service
        self._database_service = database_service
        self._pseudonym_factory = pseudonym_factory
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

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

    def select(self, item_uid: UUID, value: ItemSelect) -> Optional[Item]:
        with self._database_service.get_session() as session:
            item = self._database_service.get_item(session, item_uid)
            if item is None:
                return None
            touched = {
                touched_item.uid: touched_item
                for touched_item in self._select_item(item, value.select, session)
            }
            item.comment = value.comment
            tags = set(
                self._database_service.get_tag(session, tag) for tag in value.tags or []
            )

            if value.additive_tags:
                item.tags = item.tags.union(tags)
            else:
                item.tags = tags
            touched.setdefault(item.uid, item)
            self._validate_touched(touched.values(), session)
            return item.model

    def _validate_touched(
        self, touched: Iterable[DatabaseItem], session: Session
    ) -> None:
        """Re-validate every item whose ``selected`` flipped during a
        cascade so ``valid_relations`` reflects the new graph."""
        for touched_item in touched:
            self._validation_service.validate_item_relations(touched_item, session)

    def update(self, item: AnyItem) -> Optional[AnyItem]:
        with self._database_service.get_session() as session:
            existing_item = self._database_service.get_optional_item(session, item.uid)
            if existing_item is None or existing_item.batch is None:
                return None
            existing_item.name = item.name
            existing_item.identifier = item.identifier
            existing_item.comment = item.comment
            if isinstance(existing_item, DatabaseSample):
                if not isinstance(item, Sample):
                    raise TypeError(f"Expected Sample, got {type(item)}.")
                existing_item.parents = set(
                    self._database_service.get_sample(session, parent)
                    for schema_parents in item.parents.values()
                    for parent in schema_parents
                )
                existing_item.children = set(
                    self._database_service.get_sample(session, child)
                    for schema_children in item.children.values()
                    for child in schema_children
                )
                existing_item.images = set(
                    self._database_service.get_image(session, image)
                    for schema_images in item.images.values()
                    for image in schema_images
                )
                existing_item.observations = set(
                    self._database_service.get_observation(session, observation)
                    for schema_observations in item.observations.values()
                    for observation in schema_observations
                )
            elif isinstance(existing_item, DatabaseImage):
                if not isinstance(item, Image):
                    raise TypeError(f"Expected Image, got {type(item)}.")
                existing_item.samples = set(
                    self._database_service.get_sample(session, sample)
                    for schema_samples in item.samples.values()
                    for sample in schema_samples
                )
            elif isinstance(existing_item, DatabaseAnnotation):
                if not isinstance(item, Annotation):
                    raise TypeError(f"Expected Annotation, got {type(item)}.")
                existing_item.image = (
                    self._database_service.get_image(session, item.image[1])
                    if item.image is not None
                    else None
                )
            elif isinstance(existing_item, DatabaseObservation):
                if not isinstance(item, Observation):
                    raise TypeError(f"Expected Observation, got {type(item)}.")
                if item.sample is not None:
                    existing_item.sample = self._database_service.get_sample(
                        session, item.sample[1]
                    )
                elif item.image is not None:
                    existing_item.image = self._database_service.get_image(
                        session, item.image[1]
                    )
                elif item.annotation is not None:
                    existing_item.annotation = self._database_service.get_annotation(
                        session, item.annotation[1]
                    )
            else:
                raise TypeError(f"Unknown item type {existing_item}.")
            mappers = [
                mapper
                for group in existing_item.batch.project.mapper_groups
                for mapper in self._database_service.get_mapper_group(
                    session, group
                ).mappers
            ]
            attributes = self._mapper_service.apply_mappers_to_attributes(
                item.attributes.values(),
                mappers,
                validate=False,
                session=session,
            )
            self._attribute_service.update_for_item(
                existing_item, attributes, session=session
            )
            self._tag_service.update_for_item(existing_item, item.tags, session=session)
            self._validation_service.validate_item_relations(existing_item, session)
            return existing_item.model

    def add(
        self,
        item: AnyItem,
        mappers: Sequence[Union[DatabaseMapper, Mapper, UUID]],
        session: Optional[Session] = None,
    ) -> AnyItem:
        with self._database_service.get_session(session) as session:
            existing_item = self._database_service.get_optional_item_by_identifier(
                session, item.identifier, item.schema_uid, item.dataset_uid
            )
            if existing_item is not None:
                if isinstance(existing_item, DatabaseSample) and isinstance(
                    item, Sample
                ):
                    existing_item.children.update(
                        self._database_service.get_sample(session, child)
                        for schema_children in item.children.values()
                        for child in schema_children
                    )
                    existing_item.parents.update(
                        self._database_service.get_sample(session, parent)
                        for schema_parents in item.parents.values()
                        for parent in schema_parents
                    )
                self._logger.info(
                    f"Item {item.uid, item.identifier, item.schema_uid} already exists as {existing_item.uid}."
                )
                return existing_item.model

            attributes = self._mapper_service.apply_mappers_to_attributes(
                item.attributes.values(),
                mappers,
                validate=False,
                session=session,
            )
            database_attributes = self._attribute_service.create_or_update_attributes(
                attributes, session=session
            )
            private_attributes = (
                self._attribute_service.create_or_update_private_attributes(
                    item.private_attributes.values(), session=session
                )
            )

            database_item = self._database_service.add_item(
                session,
                item,
                attributes=database_attributes,
                private_attributes=private_attributes,
            )
            self._validation_service.validate_item_attributes(database_item, session)
            self._validation_service.validate_item_relations(database_item, session)
            session.flush()
            return database_item.model  # type: ignore

    def create(
        self,
        item_schema: Union[UUID, ItemSchema],
        dataset: Union[UUID, Dataset, DatabaseDataset],
        batch: Union[UUID, Batch, DatabaseBatch],
        target_parent_uid: Optional[UUID] = None,
        identifier: Optional[str] = None,
    ) -> Optional[AnyItem]:
        if isinstance(item_schema, UUID):
            item_schema = self._schema_service.items[item_schema]
        if isinstance(dataset, (Dataset, DatabaseDataset)):
            dataset = dataset.uid
        with self._database_service.get_session() as session:

            batch = self._database_service.get_batch(session, batch)
            mappers = [
                mapper
                for group in batch.project.mapper_groups
                for mapper in group.mappers
            ]
            initial_attributes = {
                tag: self._empty_attribute_from_schema(schema)
                for tag, schema in item_schema.attributes.items()
            }
            initial_private_attributes = {
                tag: self._empty_attribute_from_schema(schema)
                for tag, schema in item_schema.private_attributes.items()
            }
            new_item: Optional[AnyItem] = None
            if isinstance(item_schema, SampleSchema):
                sample = Sample(
                    uid=uuid.UUID(int=0),
                    identifier=identifier or "New sample",
                    dataset_uid=dataset,
                    schema_uid=item_schema.uid,
                    batch_uid=batch.uid,
                    attributes=initial_attributes,
                    private_attributes=initial_private_attributes,
                )
                new_item = self.add(sample, mappers, session=session)
            elif isinstance(item_schema, ImageSchema):
                image = Image(
                    uid=uuid.UUID(int=0),
                    identifier=identifier or "New image",
                    dataset_uid=dataset,
                    schema_uid=item_schema.uid,
                    batch_uid=batch.uid,
                    format=ImageFormat.OTHER_WSI,
                    attributes=initial_attributes,
                    private_attributes=initial_private_attributes,
                )
                new_item = self.add(image, mappers, session=session)
            elif isinstance(item_schema, AnnotationSchema):
                annotation = Annotation(
                    uid=uuid.UUID(int=0),
                    identifier=identifier or "New annotation",
                    dataset_uid=dataset,
                    schema_uid=item_schema.uid,
                    batch_uid=batch.uid,
                    attributes=initial_attributes,
                    private_attributes=initial_private_attributes,
                )
                new_item = self.add(annotation, mappers, session=session)
            elif isinstance(item_schema, ObservationSchema):
                observation = Observation(
                    uid=uuid.UUID(int=0),
                    identifier=identifier or "New observation",
                    dataset_uid=dataset,
                    schema_uid=item_schema.uid,
                    batch_uid=batch.uid,
                    attributes=initial_attributes,
                    private_attributes=initial_private_attributes,
                )
                new_item = self.add(observation, mappers, session=session)
            else:
                raise TypeError(f"Unknown item schema {item_schema}.")

            if target_parent_uid is not None:
                self.change_relations(
                    [
                        RelationChange(
                            item_uid=new_item.uid, target_item_uid=target_parent_uid
                        )
                    ],
                    session=session,
                )
            return new_item

    def get_for_schema(
        self,
        item_schema_uid: UUID,
        dataset_uid: UUID,
        batch_uid: Optional[UUID] = None,
        start: Optional[int] = None,
        size: Optional[int] = None,
        identifier_filter: Optional[str] = None,
        pseudonym_mode: bool = False,
        attribute_filters: Optional[Dict[str, str]] = None,
        relation_filters: Optional[Iterable[RelationFilter]] = None,
        tag_filter: Optional[Iterable[UUID]] = None,
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
                pseudonym_mode,
                attribute_filters,
                relation_filters,
                tag_filter,
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
        pseudonym_mode: bool = False,
        attribute_filters: Optional[Dict[str, str]] = None,
        relation_filters: Optional[Iterable[RelationFilter]] = None,
        tag_filter: Optional[Iterable[UUID]] = None,
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
                pseudonym_mode,
                attribute_filters,
                relation_filters,
                tag_filter,
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
        pseudonym_mode: bool = False,
        attribute_filters: Optional[Dict[str, str]] = None,
        relation_filters: Optional[Iterable[RelationFilter]] = None,
        tag_filter: Optional[Iterable[UUID]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
        status_filter: Optional[Iterable[ImageStatus]] = None,
    ) -> int:
        item_schema = self._schema_service.items[item_schema_uid]

        with self._database_service.get_session() as session:
            return self._database_service.get_item_count(
                session,
                item_schema,
                dataset_uid,
                batch_uid,
                identifier_filter,
                pseudonym_mode,
                attribute_filters,
                relation_filters=relation_filters,
                tag_filter=tag_filter,
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
            touched = {
                touched_item.uid: touched_item
                for touched_item in self._select_item(item, value, session)
            }
            self._validate_touched(touched.values(), session)

    def _select_item(
        self,
        item: Union[UUID, Item, DatabaseItem],
        value: bool,
        session: Session,
    ) -> Iterable[DatabaseItem]:
        if isinstance(item, UUID):
            item = self._database_service.get_item(session, item)
        if isinstance(item, (Sample, DatabaseSample)):
            yield from self._select_sample(item, value, session)
        elif isinstance(item, (Image, DatabaseImage)):
            yield from self._select_image(item, value, session)
        elif isinstance(item, (Annotation, DatabaseAnnotation)):
            yield from self._select_annotation(item, value, session)
        elif isinstance(item, (Observation, DatabaseObservation)):
            yield from self._select_observation(item, value, session)

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
            touched = {
                touched_item.uid: touched_item
                for touched_item in self._select_image(image, value, session)
            }
            self._validate_touched(touched.values(), session)

    def _select_image(
        self,
        image: Union[UUID, Image, DatabaseImage],
        value: bool,
        session: Session,
    ) -> Iterable[DatabaseItem]:
        image = self._database_service.get_image(session, image)
        yield from self._set_selected(image, value)
        if value:
            for sample in image.samples:
                yield from self._select_sample(sample, True, session)
        else:
            for observation in image.observations:
                yield from self._set_selected(observation, False)
            for annotation in image.annotations:
                yield from self._set_selected(annotation, False)

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
            touched = {
                touched_item.uid: touched_item
                for touched_item in self._select_sample(sample, value, session)
            }
            self._validate_touched(touched.values(), session)

    def _select_sample(
        self,
        sample: Union[UUID, Sample, DatabaseSample],
        value: bool,
        session: Session,
    ) -> Iterable[DatabaseItem]:
        sample = self._database_service.get_sample(session, sample)
        yield from self._set_selected(sample, value)
        for child in sample.children:
            yield from self._select_sample_from_parent(child, value)
        for parent in sample.parents:
            yield from self._select_sample_from_child(parent, value)
        if not value:
            for observation in sample.observations:
                yield from self._set_selected(observation, False)
            for image in sample.images:
                yield from self._set_selected(image, False)

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
            touched = {
                touched_item.uid: touched_item
                for touched_item in self._select_observation(
                    observation, value, session
                )
            }
            self._validate_touched(touched.values(), session)

    def _select_observation(
        self,
        observation: Union[UUID, Observation, DatabaseObservation],
        value: bool,
        session: Session,
    ) -> Iterable[DatabaseItem]:
        observation = self._database_service.get_observation(session, observation)
        yield from self._set_selected(observation, value)
        if value:
            yield from self._select_item(observation.item, True, session)

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
            touched = {
                touched_item.uid: touched_item
                for touched_item in self._select_annotation(annotation, value, session)
            }
            self._validate_touched(touched.values(), session)

    def _select_annotation(
        self,
        annotation: Union[UUID, Annotation, DatabaseAnnotation],
        value: bool,
        session: Session,
    ) -> Iterable[DatabaseItem]:
        annotation = self._database_service.get_annotation(session, annotation)
        yield from self._set_selected(annotation, value)
        if value and annotation.image is not None:
            yield from self._select_item(annotation.image, True, session)

    def copy(
        self,
        item: Union[UUID, Item, DatabaseItem],
        target_parent_uid: Optional[UUID] = None,
        identifier: Optional[str] = None,
    ) -> AnyItem:
        with self._database_service.get_session() as session:
            copy = self._database_service.get_item(session, item).model
            copy.uid = uuid.uuid4()
            copy.identifier = identifier or f"{copy.identifier} (copy)"
            copy.name = f"{copy.name} (copy)" if copy.name else None
            copy.pseudonym = (
                self._pseudonym_factory.create_pseudonym(copy)
                if self._pseudonym_factory
                else None
            )
            for attribute in copy.attributes.values():
                attribute.uid = uuid.uuid4()
            attributes = self._attribute_service.create_or_update_attributes(
                copy.attributes.values(), session=session
            )
            for private_attribute in copy.private_attributes.values():
                private_attribute.uid = uuid.uuid4()
            private_attributes = (
                self._attribute_service.create_or_update_private_attributes(
                    copy.private_attributes.values(), session=session
                )
            )
            self._database_service.add_item(
                session, copy, attributes, private_attributes
            )
            if target_parent_uid is not None:
                self.change_relations(
                    [
                        RelationChange(
                            item_uid=copy.uid, target_item_uid=target_parent_uid
                        )
                    ],
                    session=session,
                )
            assert isinstance(copy, (Sample, Image, Annotation, Observation))
            return copy

    def split_sample(
        self,
        original: Union[UUID, Sample, DatabaseSample],
        splits: Iterable[Dict[UUID, List[UUID]]],
        batch_uid: Optional[UUID] = None,
    ) -> Iterable[AnyItem]:
        with self._database_service.get_session() as session:
            original = self._database_service.get_sample(session, original).model
            new_samples = []
            for index, children in enumerate(splits):
                split = self._database_service.get_sample(session, original).model
                split.uid = uuid.uuid4()
                split.identifier = f"{original.identifier} ({index + 1})"
                split.name = f"{original.name} ({index + 1})" if original.name else None
                split.batch_uid = batch_uid or original.batch_uid
                split.pseudonym = (
                    self._pseudonym_factory.create_pseudonym(split)
                    if self._pseudonym_factory
                    else None
                )
                for attribute in split.attributes.values():
                    attribute.uid = uuid.uuid4()
                attributes = self._attribute_service.create_or_update_attributes(
                    split.attributes.values(), session=session
                )
                for private_attribute in split.private_attributes.values():
                    private_attribute.uid = uuid.uuid4()
                private_attributes = (
                    self._attribute_service.create_or_update_private_attributes(
                        split.private_attributes.values(), session=session
                    )
                )
                split.children = children
                split = self._database_service.add_item(
                    session, split, attributes, private_attributes
                )
                new_samples.append(split)
                yield split.model
                for schema_uid, children_uids in children.items():
                    for child_uid in children_uids:
                        original.children[schema_uid].remove(child_uid)
            yield original

    def _collect_section_attributes(
        self,
        item_model: Item,
        section: OverviewSectionLayout,
    ) -> tuple[Dict[str, AnyAttribute], Dict[str, AnyAttribute]]:
        """Collect attributes and private attributes for a section.

        Returns a tuple of (attributes, private_attributes).
        """
        attributes: Dict[str, AnyAttribute] = {}
        if section.attributes:
            for tag in section.attributes:
                attr = self._resolve_attribute(item_model.attributes, tag)
                if attr is not None:
                    attributes[tag] = attr
        else:
            attributes.update(item_model.attributes)

        private_attributes: Dict[str, AnyAttribute] = {}
        if section.private_attributes:
            for tag in section.private_attributes:
                attr = self._resolve_attribute(item_model.private_attributes, tag)
                if attr is not None:
                    private_attributes[tag] = attr
        else:
            private_attributes.update(item_model.private_attributes)

        return attributes, private_attributes

    @staticmethod
    def _resolve_attribute(
        attributes: Dict[str, AnyAttribute],
        tag: str,
    ) -> Optional[AnyAttribute]:
        """Resolve a possibly nested attribute tag.

        Supports compound tags like "parent_tag.child_tag" to reach into
        ObjectAttribute values.
        """
        if tag in attributes:
            return attributes[tag]
        # Try compound tag: split on "." and walk into ObjectAttributes
        parts = tag.split(".", 1)
        if len(parts) == 2:
            parent_tag, child_tag = parts
            parent_attr = attributes.get(parent_tag)
            if isinstance(parent_attr, ObjectAttribute):
                for value_dict in (
                    parent_attr.updated_value,
                    parent_attr.mapped_value,
                    parent_attr.original_value,
                ):
                    if value_dict and child_tag in value_dict:
                        return value_dict[child_tag]
        return None

    def change_relations(
        self,
        changes: List[RelationChange],
        session: Optional[Session] = None,
    ) -> None:
        """Change item-to-item relations.

        Each change specifies an item and its new target (parent/related item).
        The relation type is determined by the item types involved.
        """
        with self._database_service.get_session(session) as session:
            for change in changes:
                item = self._database_service.get_item(session, change.item_uid)
                target = self._database_service.get_item(
                    session, change.target_item_uid
                )

                if isinstance(item, DatabaseObservation):
                    if isinstance(target, DatabaseSample):
                        item.image = None
                        item.annotation = None
                        item.sample = target
                    elif isinstance(target, DatabaseImage):
                        item.sample = None
                        item.annotation = None
                        item.image = target
                    elif isinstance(target, DatabaseAnnotation):
                        item.sample = None
                        item.image = None
                        item.annotation = target
                    else:
                        raise ValueError(
                            f"Cannot relate observation {item.uid} "
                            f"to {type(target).__name__} {target.uid}"
                        )
                elif isinstance(item, DatabaseAnnotation):
                    if isinstance(target, DatabaseImage):
                        item.image = target
                    else:
                        raise ValueError(
                            f"Cannot relate annotation {item.uid} "
                            f"to {type(target).__name__} {target.uid}"
                        )
                elif isinstance(item, DatabaseImage):
                    if isinstance(target, DatabaseSample):
                        if change.source_item_uid is not None:
                            source = self._database_service.get_optional_item(
                                session, change.source_item_uid
                            )
                            if isinstance(source, DatabaseSample):
                                item.samples.discard(source)
                        item.samples.add(target)
                    else:
                        raise ValueError(
                            f"Cannot relate image {item.uid} "
                            f"to {type(target).__name__} {target.uid}"
                        )
                elif isinstance(item, DatabaseSample):
                    if isinstance(target, DatabaseSample):
                        if change.source_item_uid is not None:
                            source = self._database_service.get_optional_item(
                                session, change.source_item_uid
                            )
                            if isinstance(source, DatabaseSample):
                                item.parents.discard(source)
                        item.parents.add(target)
                    else:
                        raise ValueError(
                            f"Cannot relate sample {item.uid} "
                            f"to {type(target).__name__} {target.uid}"
                        )
                else:
                    raise ValueError(f"Unsupported item type {type(item).__name__}")

    def get_overview_data(
        self,
        item_uid: UUID,
        overview_layout: OverviewLayout,
        pseudonym_mode: bool = False,
    ) -> Optional[OverviewRoot]:
        with self._database_service.get_session() as session:
            parent = self._database_service.get_optional_item(session, item_uid)
            if parent is None:
                return None
            if not isinstance(parent, DatabaseSample):
                raise ValueError(
                    f"Overview is only supported for sample items, "
                    f"got {type(parent).__name__} for item {item_uid}"
                )

            # Build sections from layout
            sections: List[OverviewSection] = []

            for section in overview_layout.sections:
                target_schema = self._schema_service.items.get(section.schema_uid)
                if target_schema is None:
                    self._logger.warning(
                        f"Section target schema {section.schema_uid} "
                        f"not found, skipping"
                    )
                    continue

                # If target is the parent itself, show parent's attributes
                if section.schema_uid == parent.schema_uid:
                    attrs, private_attrs = self._collect_section_attributes(
                        parent.model, section
                    )
                    sections.append(
                        OverviewSection(
                            item_uid=parent.uid,
                            label=(section.display_name or parent.identifier),
                            pseudonym=(
                                None if section.display_name else parent.pseudonym
                            ),
                            schema_uid=section.schema_uid,
                            items=[
                                OverviewItem(
                                    item_uid=parent.uid,
                                    identifier=parent.identifier,
                                    pseudonym=parent.pseudonym,
                                    attributes=attrs,
                                    private_attributes=private_attrs,
                                )
                            ],
                        )
                    )
                    continue

                # Traverse the path from root to find parent items
                if not section.path:
                    # No path = parent is the root itself
                    group_items = [parent]
                else:
                    # Walk path step by step to reach parent items
                    current_items: List[DatabaseSample] = [parent]
                    for step_schema_uid in section.path:
                        next_items: List[DatabaseSample] = []
                        for item in current_items:
                            next_items.extend(
                                self._database_service.get_sample_children(
                                    session, item, step_schema_uid
                                )
                            )
                        current_items = next_items
                    group_items = sorted(current_items, key=lambda c: c.identifier)

                for group_child in group_items:
                    target_items: List[OverviewItem] = []

                    if isinstance(target_schema, ObservationSchema):
                        for observation in group_child.observations:
                            if observation.schema_uid != section.schema_uid:
                                continue
                            obs_model = observation.model
                            attrs, private_attrs = self._collect_section_attributes(
                                obs_model, section
                            )
                            target_items.append(
                                OverviewItem(
                                    item_uid=observation.uid,
                                    identifier=observation.identifier,
                                    pseudonym=observation.pseudonym,
                                    attributes=attrs,
                                    private_attributes=private_attrs,
                                )
                            )
                    elif isinstance(target_schema, SampleSchema):
                        children = self._database_service.get_sample_children(
                            session,
                            group_child,
                            section.schema_uid,
                            recursive=True,
                        )
                        for child in sorted(children, key=lambda c: c.identifier):
                            child_model = child.model
                            attrs, private_attrs = self._collect_section_attributes(
                                child_model, section
                            )
                            target_items.append(
                                OverviewItem(
                                    item_uid=child.uid,
                                    identifier=child.identifier,
                                    pseudonym=child.pseudonym,
                                    attributes=attrs,
                                    private_attributes=private_attrs,
                                )
                            )
                    else:
                        self._logger.warning(
                            f"Unsupported target schema type "
                            f"{type(target_schema).__name__} in overview section"
                        )

                    if target_items or section.creatable:
                        use_section_label = section.display_name and not section.path
                        sections.append(
                            OverviewSection(
                                item_uid=group_child.uid,
                                label=(
                                    section.display_name
                                    if use_section_label
                                    else group_child.identifier
                                ),
                                pseudonym=(
                                    None if use_section_label else group_child.pseudonym
                                ),
                                schema_uid=section.schema_uid,
                                items=target_items,
                            )
                        )

            # Find previous/next sibling parent items
            previous_uid = None
            next_uid = None
            parent_schema = self._schema_service.samples.get(parent.schema_uid)
            if parent_schema is not None:
                siblings = list(
                    self._database_service.get_samples(
                        session,
                        parent_schema,
                        parent.dataset_uid,
                    )
                )

                def _sort_key(s: DatabaseSample) -> str:
                    if not pseudonym_mode:
                        return s.identifier
                    if s.pseudonym:
                        return s.pseudonym
                    return f"ANON-{str(s.uid)[:8].upper()}"

                siblings.sort(key=_sort_key)
                for i, sibling in enumerate(siblings):
                    if sibling.uid == parent.uid:
                        if i > 0:
                            previous_uid = siblings[i - 1].uid
                        if i < len(siblings) - 1:
                            next_uid = siblings[i + 1].uid
                        break

            return OverviewRoot(
                item_uid=parent.uid,
                identifier=parent.identifier,
                pseudonym=parent.pseudonym,
                sections=sections,
                previous_uid=previous_uid,
                next_uid=next_uid,
            )

    def _set_selected(
        self,
        item: DatabaseItem,
        value: bool,
    ) -> Iterable[DatabaseItem]:
        """Set ``item.selected`` and yield ``item`` if the value
        actually changed. Items yielded by this and the surrounding
        cascade get re-validated by the caller after the cascade
        completes."""
        if item.selected == value:
            return
        item.selected = value
        yield item

    def _select_sample_from_parent(
        self,
        child: DatabaseSample,
        parent_selected: bool,
    ) -> Iterable[DatabaseItem]:
        """Select or deselect a child based on the selection of one parent.

        If all parents are selected, the child is selected.
        If the parent is deselected, the child is deselected.
        Recurse the child selection to all children, images, and observations."""
        if parent_selected:
            if all(parent.selected for parent in child.parents):
                yield from self._set_selected(child, True)
        else:
            yield from self._set_selected(child, False)
        for child_child in child.children:
            yield from self._select_sample_from_parent(child_child, child.selected)
        for image in child.images:
            yield from self._select_image_from_sample(image, child.selected)
        for observation in child.observations:
            yield from self._set_selected(observation, child.selected)

    def _select_sample_from_child(
        self,
        parent: DatabaseSample,
        child_selected: bool,
    ) -> Iterable[DatabaseItem]:
        """Select or deselect a parent based on the selection of one child.

        If one child is selected, the parent is selected.
        If all children are deselected, the parent is deselected.
        Recurse the parent selection to all parents, images, and observations.

        """
        if child_selected:
            yield from self._set_selected(parent, True)
        elif all(not child.selected for child in parent.children):
            yield from self._set_selected(parent, False)
        for parent_parent in parent.parents:
            yield from self._select_sample_from_child(parent_parent, child_selected)
        for image in parent.images:
            yield from self._select_image_from_sample(image, child_selected)
        for observation in parent.observations:
            yield from self._set_selected(observation, child_selected)

    def _select_image_from_sample(
        self,
        image: DatabaseImage,
        sample_selection: bool,
    ) -> Iterable[DatabaseItem]:
        """Select or deselect an image based on the selection of one sample.

        If the sample is deselected, the image and its annotations and observations are
        deselected.
        If all samples are selected, the image is selected.
        """
        if not sample_selection:
            yield from self._set_selected(image, False)
            for annotation in image.annotations:
                yield from self._set_selected(annotation, False)
            for observation in image.observations:
                yield from self._set_selected(observation, False)
        elif all(sample.selected for sample in image.samples):
            yield from self._set_selected(image, True)

    def _get_for_schema(
        self,
        session: Session,
        item_schema_uid: UUID,
        dataset_uid: Optional[UUID] = None,
        batch_uid: Optional[UUID] = None,
        start: Optional[int] = None,
        size: Optional[int] = None,
        identifier_filter: Optional[str] = None,
        pseudonym_mode: bool = False,
        attribute_filters: Optional[Dict[str, str]] = None,
        relation_filters: Optional[Iterable[RelationFilter]] = None,
        tag_filter: Optional[Iterable[UUID]] = None,
        sorting: Optional[Iterable[ColumnSort]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
        status_filter: Optional[Iterable[ImageStatus]] = None,
    ) -> Iterable[DatabaseItem]:
        item_schema = self._schema_service.items[item_schema_uid]
        if isinstance(item_schema, SampleSchema):
            items = self._database_service.get_samples(
                session,
                item_schema,
                dataset_uid,
                batch_uid,
                start,
                size,
                identifier_filter,
                pseudonym_mode,
                attribute_filters,
                tag_filter,
                relation_filters,
                sorting,
                selected,
                valid,
            )
        elif isinstance(item_schema, ImageSchema):
            items = self._database_service.get_images(
                session,
                item_schema,
                dataset_uid,
                batch_uid,
                start,
                size,
                identifier_filter,
                pseudonym_mode,
                attribute_filters,
                tag_filter,
                relation_filters,
                sorting,
                selected,
                valid,
                status_filter,
            )
        elif isinstance(item_schema, AnnotationSchema):
            items = self._database_service.get_annotations(
                session,
                item_schema,
                dataset_uid,
                batch_uid,
                start,
                size,
                identifier_filter,
                pseudonym_mode,
                attribute_filters,
                tag_filter,
                relation_filters,
                sorting,
                selected,
                valid,
            )
        elif isinstance(item_schema, ObservationSchema):
            items = self._database_service.get_observations(
                session,
                item_schema,
                dataset_uid,
                batch_uid,
                start,
                size,
                identifier_filter,
                pseudonym_mode,
                attribute_filters,
                tag_filter,
                relation_filters,
                sorting,
                selected,
                valid,
            )
        else:
            raise TypeError(f"Unknown item type {item_schema}.")

        return items

    @staticmethod
    def _empty_attribute_from_schema(schema: AttributeSchema) -> AnyAttribute:
        """Construct an empty attribute matching ``schema``.

        Used when creating new items so the schema-defined attribute structure
        exists immediately. Without this, freshly-created items have no
        attributes at all and editors that reach into nested ObjectAttributes
        (e.g. ``statement.diagnose``) have nothing to merge into.

        Children of ObjectAttributes are not pre-materialised — clients render
        placeholders for missing children from the schema and the deep-merge on
        save fills them in.
        """
        base = {
            "uid": uuid.uuid4(),
            "schema_uid": schema.uid,
            "valid": schema.optional,
        }
        if isinstance(schema, StringAttributeSchema):
            return StringAttribute(**base)
        if isinstance(schema, EnumAttributeSchema):
            return EnumAttribute(**base)
        if isinstance(schema, DatetimeAttributeSchema):
            return DatetimeAttribute(**base)
        if isinstance(schema, NumericAttributeSchema):
            return NumericAttribute(**base)
        if isinstance(schema, MeasurementAttributeSchema):
            return MeasurementAttribute(**base)
        if isinstance(schema, CodeAttributeSchema):
            return CodeAttribute(**base)
        if isinstance(schema, BooleanAttributeSchema):
            return BooleanAttribute(**base)
        if isinstance(schema, ObjectAttributeSchema):
            return ObjectAttribute(**base)
        if isinstance(schema, ListAttributeSchema):
            return ListAttribute(**base)
        if isinstance(schema, UnionAttributeSchema):
            return UnionAttribute(**base)
        raise TypeError(f"Unknown attribute schema type {type(schema).__name__}.")
