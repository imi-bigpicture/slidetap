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
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Union
from uuid import UUID

from sqlalchemy.orm import Session

from slidetap.database import (
    DatabaseAnnotation,
    DatabaseBatch,
    DatabaseImage,
    DatabaseItem,
    DatabaseObservation,
    DatabaseSample,
)
from slidetap.database.mapper import DatabaseMapper
from slidetap.external_interfaces import (
    ItemNamingFactoryInterface,
    PseudonymFactoryInterface,
)
from slidetap.model import (
    AnyItem,
    Annotation,
    AnnotationSchema,
    Batch,
    ColumnSort,
    Image,
    ImageFormat,
    ImageGroup,
    ImageSchema,
    ImageStatus,
    Item,
    ItemReference,
    ItemSchema,
    Mapper,
    Observation,
    ObservationSchema,
    Sample,
    SampleSchema,
)
from slidetap.model.item_select import ItemSelect
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
        item_naming_factory: Optional[ItemNamingFactoryInterface] = None,
    ) -> None:
        self._attribute_service = attribute_service
        self._tag_service = tag_service
        self._mapper_service = mapper_service
        self._schema_service = schema_service
        self._validation_service = validation_service
        self._database_service = database_service
        self._pseudonym_factory = pseudonym_factory
        self._item_naming_factory = item_naming_factory
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def get(self, item_uid: UUID) -> AnyItem:
        with self._database_service.get_session() as session:
            return self._database_service.get_item(session, item_uid).model

    def get_optional(self, item_uid: UUID) -> Optional[AnyItem]:
        with self._database_service.get_session() as session:
            item = self._database_service.get_optional_item(session, item_uid)
            return item.model if item is not None else None

    def get_sample(self, item_uid: UUID) -> Sample:
        with self._database_service.get_session() as session:
            return self._database_service.get_sample(session, item_uid).model

    def get_optional_sample(self, item_uid: UUID) -> Optional[Sample]:
        with self._database_service.get_session() as session:
            item = self._database_service.get_optional_sample(session, item_uid)
            return item.model if item is not None else None

    def get_image(self, item_uid: UUID) -> Image:
        with self._database_service.get_session() as session:
            return self._database_service.get_image(session, item_uid).model

    def get_optional_image(self, item_uid: UUID) -> Optional[Image]:
        with self._database_service.get_session() as session:
            item = self._database_service.get_optional_image(session, item_uid)
            return item.model if item is not None else None

    def get_annotation(self, item_uid: UUID) -> Annotation:
        with self._database_service.get_session() as session:
            return self._database_service.get_annotation(session, item_uid).model

    def get_optional_annotation(self, item_uid: UUID) -> Optional[Annotation]:
        with self._database_service.get_session() as session:
            item = self._database_service.get_optional_annotation(session, item_uid)
            return item.model if item is not None else None

    def get_observation(self, item_uid: UUID) -> Observation:
        with self._database_service.get_session() as session:
            return self._database_service.get_observation(session, item_uid).model

    def get_optional_observation(self, item_uid: UUID) -> Optional[Observation]:
        with self._database_service.get_session() as session:
            item = self._database_service.get_optional_observation(session, item_uid)
            return item.model if item is not None else None

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

    def select(self, item_uid: UUID, value: ItemSelect) -> Optional[AnyItem]:
        with self._database_service.get_session() as session:
            item = self._database_service.get_optional_item(session, item_uid)
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
        mappers: Optional[Sequence[Union[DatabaseMapper, Mapper, UUID]]] = None,
        session: Optional[Session] = None,
    ) -> AnyItem:
        with self._database_service.get_session(session) as session:
            if mappers is None:
                mappers = self._mappers_for_item(item, session)
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
            self._validation_service.validate_item_pseudonym(database_item, session)
            self._validation_service.validate_item_relations(database_item, session)
            session.flush()
            return database_item.model

    def create(
        self,
        item_schema: Union[UUID, ItemSchema],
        batch: Union[UUID, Batch, DatabaseBatch],
        target_parent_uids: Optional[Sequence[UUID]] = None,
        identifier: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> Optional[AnyItem]:
        """Create a new item and persist it in one atomic ``add()`` call."""
        if isinstance(item_schema, UUID):
            item_schema = self._schema_service.items[item_schema]
        parent_uids = list(target_parent_uids or ())
        with self._database_service.get_session(session) as session:
            batch = self._database_service.get_batch(session, batch)
            mappers = [
                mapper
                for group in batch.project.mapper_groups
                for mapper in group.mappers
            ]
            parents = self._validate_target_parents(item_schema, parent_uids, session)
            new_item = self._build_new_item_model(
                item_schema, batch.project.dataset_uid, batch.uid, parents
            )
            new_item.identifier = self._resolve_identifier(new_item, identifier)
            new_item.name = self._resolve_name(new_item)
            new_item.pseudonym = self._resolve_pseudonym(new_item)
            return self.add(new_item, mappers, session=session)

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
                load_relations=True,
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
    ) -> None:
        """Select or deselect ``item`` and cascade per its concrete type.

        - Sample: cascades to children and parents; on deselect also
          deselects observations and images.
        - Image: on select also selects parent samples; on deselect also
          deselects observations and annotations.
        - Observation: on select also selects the item it observes.
        - Annotation: on select also selects the image it is attached to.

        Every item whose ``selected`` flag flips is re-validated so
        ``valid_relations`` reflects the new graph.
        """
        with self._database_service.get_session(session) as session:
            touched = {
                touched_item.uid: touched_item
                for touched_item in self._select_item(item, value, session)
            }
            self._validate_touched(touched.values(), session)

    def copy(
        self,
        item: Union[UUID, Item, DatabaseItem],
        target_parent_uids: Optional[Sequence[UUID]] = None,
        identifier: Optional[str] = None,
    ) -> AnyItem:
        parent_uids = list(target_parent_uids or ())
        with self._database_service.get_session() as session:
            source = self._database_service.get_item(session, item)
            source_schema = self._schema_service.items[source.schema_uid]
            parents = self._validate_target_parents(source_schema, parent_uids, session)
            copy = source.model
            copy.uid = uuid.uuid4()
            self._replace_parent_relations(copy, parents)
            copy.identifier = self._resolve_identifier(copy, identifier)
            copy.name = self._resolve_name(copy)
            copy.pseudonym = self._resolve_pseudonym(copy)
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
            database_copy = self._database_service.add_item(
                session, copy, attributes, private_attributes
            )
            self._validation_service.validate_item_pseudonym(database_copy, session)
            return database_copy.model

    def split_sample(
        self,
        original: Union[UUID, Sample, DatabaseSample],
        splits: Iterable[Mapping[UUID, Sequence[UUID]]],
        batch_uid: Optional[UUID] = None,
    ) -> Iterable[AnyItem]:
        """Split a sample into multiple new samples that share its parents.

        Each entry in ``splits`` is a ``{child_schema_uid: [child_uid, ...]}``
        mapping describing the children that move from the original to that
        new split. The new splits inherit ``original``'s parents,
        attributes, and (factory-generated) pseudonym; they get a
        factory-generated identifier seeded from those shared parents.
        Images and observations stay with the original.

        Yields each new split's model, then the updated original's model
        at the end.
        """
        splits = list(splits)
        with self._database_service.get_session() as session:
            original_db = self._database_service.get_sample(session, original)
            for child_assignment in splits:
                split = original_db.model
                split.uid = uuid.uuid4()
                split.batch_uid = batch_uid or split.batch_uid
                # Keep inherited parents (splits are siblings of the
                # original under the same parents). Children become the
                # assigned subset only; images/observations stay with the
                # original.
                split.children = {
                    schema_uid: list(child_uids)
                    for schema_uid, child_uids in child_assignment.items()
                }
                split.images = {}
                split.observations = {}
                split.identifier = self._resolve_identifier(split, None)
                split.name = self._resolve_name(split)
                split.pseudonym = self._resolve_pseudonym(split)
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
                database_split = self._database_service.add_item(
                    session, split, attributes, private_attributes
                )
                self._validation_service.validate_item_pseudonym(
                    database_split, session
                )
                # The assigned children now have both the original and the
                # new split as parents (SQLAlchemy back_populates the
                # many-to-many on add_item). Detach them from the original
                # so they live only under the split.
                for child_uid in (
                    uid for uids in child_assignment.values() for uid in uids
                ):
                    child_db = self._database_service.get_sample(session, child_uid)
                    original_db.children.discard(child_db)
                yield database_split.model
            yield original_db.model

    def move_attribute(
        self,
        source_item_uid: UUID,
        attribute_tag: str,
        target_item_uid: Optional[UUID] = None,
        target_parent_uid: Optional[UUID] = None,
        session: Optional[Session] = None,
    ) -> Optional[UUID]:
        """Swap a single attribute value between two items.

        Exactly one of ``target_item_uid`` or ``target_parent_uid`` must be
        set. When ``target_item_uid`` is given, the swap happens with that
        existing item. When ``target_parent_uid`` is given instead, a new
        item with the source's schema is created under that parent (using
        :py:meth:`create`) and the swap happens with it.

        ``attribute_tag`` may be a top-level tag or a compound
        ``parent.child`` tag pointing at an ObjectAttribute child.

        Returns the UID of a newly-created target item, or ``None`` if an
        existing target item was reused.
        """
        if (target_item_uid is None) == (target_parent_uid is None):
            raise ValueError(
                "Exactly one of target_item_uid or target_parent_uid is required"
            )
        with self._database_service.get_session(session) as session:
            source = self._database_service.get_item(session, source_item_uid)
            if source is None:
                raise ValueError(f"Source item {source_item_uid} not found")

            created_uid: Optional[UUID] = None
            if target_item_uid is not None:
                target = self._database_service.get_item(session, target_item_uid)
                if target is None:
                    raise ValueError(f"Target item {target_item_uid} not found")
                if target.schema_uid != source.schema_uid:
                    raise ValueError(
                        f"Cannot swap attribute between items of different "
                        f"schemas (source {source.schema_uid}, target "
                        f"{target.schema_uid})"
                    )
            else:
                new_model = self.create(
                    source.schema_uid,
                    source.batch_uid,
                    target_parent_uids=(
                        (target_parent_uid,) if target_parent_uid else None
                    ),
                    session=session,
                )
                if new_model is None:
                    raise RuntimeError(
                        f"Failed to create target item under {target_parent_uid}"
                    )
                target = self._database_service.get_item(session, new_model.uid)
                created_uid = new_model.uid

            self._attribute_service.swap_attribute_value(source, target, attribute_tag)

            self._validation_service.validate_item_attributes(source, session)
            self._validation_service.validate_item_attributes(target, session)
            return created_uid

    def _validate_touched(
        self, touched: Iterable[DatabaseItem], session: Session
    ) -> None:
        """Re-validate every item whose ``selected`` flipped during a
        cascade so ``valid_relations`` reflects the new graph."""
        for touched_item in touched:
            self._validation_service.validate_item_relations(touched_item, session)

    def _mappers_for_item(
        self, item: AnyItem, session: Session
    ) -> List[DatabaseMapper]:
        """Resolve the mappers from every group on the item's batch's project.

        Used by ``add()`` when no explicit mapper list is supplied (e.g.
        the ``POST /api/items/add`` route, which has no batch context of
        its own). Returns ``[]`` for items without a batch.
        """
        if item.batch_uid is None:
            return []
        batch = self._database_service.get_batch(session, item.batch_uid)
        return [
            mapper
            for group in batch.project.mapper_groups
            for mapper in group.mappers
        ]

    def _validate_target_parents(
        self,
        item_schema: ItemSchema,
        parent_uids: Sequence[UUID],
        session: Session,
    ) -> List[AnyItem]:
        """Validate parent UIDs against schema constraints and return their
        Pydantic models. Shared by ``create`` and ``copy`` so the rules
        ``allowed parent schemas``, ``per-schema max_parents`` and the
        structural single-parent cap for Observation/Annotation are enforced
        consistently before any write hits the DB.
        """
        if len(parent_uids) > 1 and isinstance(
            item_schema, (ObservationSchema, AnnotationSchema)
        ):
            raise ValueError(
                f"{type(item_schema).__name__} only supports a single parent, "
                f"got {len(parent_uids)}"
            )
        parent_schema_caps = self._schema_service.parent_schema_caps(item_schema)
        parents: List[AnyItem] = []
        count_by_parent_schema: Dict[UUID, int] = {}
        for parent_uid in parent_uids:
            parent_db = self._database_service.get_item(session, parent_uid)
            if parent_db.schema_uid not in parent_schema_caps:
                raise ValueError(
                    f"Parent item {parent_uid} has schema "
                    f"{parent_db.schema_uid}, which is not an allowed "
                    f"parent schema for {item_schema.name}"
                )
            count_by_parent_schema[parent_db.schema_uid] = (
                count_by_parent_schema.get(parent_db.schema_uid, 0) + 1
            )
            cap = parent_schema_caps[parent_db.schema_uid]
            if cap is not None and count_by_parent_schema[parent_db.schema_uid] > cap:
                raise ValueError(
                    f"Schema '{item_schema.name}' allows at most {cap} "
                    f"parent(s) of schema {parent_db.schema_uid}, got "
                    f"{count_by_parent_schema[parent_db.schema_uid]}"
                )
            parents.append(parent_db.model)
        return parents

    @staticmethod
    def _replace_parent_relations(item: AnyItem, parents: Sequence[Item]) -> None:
        """Drop any inherited relations on ``item`` and install ``parents``
        on the per-type relation field. Used by ``copy`` to ensure the new
        item lives only under the supplied parents instead of inheriting
        the source's parent/child set when ``add_item`` writes it.
        """
        if isinstance(item, Sample):
            item.parents = {}
            item.children = {}
            item.images = {}
            item.observations = {}
            for parent in parents:
                item.parents.setdefault(parent.schema_uid, []).append(parent.uid)
        elif isinstance(item, Image):
            item.samples = {}
            item.annotations = {}
            item.observations = {}
            for parent in parents:
                item.samples.setdefault(parent.schema_uid, []).append(parent.uid)
        elif isinstance(item, Annotation):
            item.image = None
            item.observation = {}
            if parents:
                item.image = (parents[0].schema_uid, parents[0].uid)
        elif isinstance(item, Observation):
            item.sample = None
            item.image = None
            item.annotation = None
            if parents:
                parent = parents[0]
                if isinstance(parent, Sample):
                    item.sample = (parent.schema_uid, parent.uid)
                elif isinstance(parent, Image):
                    item.image = (parent.schema_uid, parent.uid)
                elif isinstance(parent, Annotation):
                    item.annotation = (parent.schema_uid, parent.uid)

    def _build_new_item_model(
        self,
        item_schema: ItemSchema,
        dataset_uid: UUID,
        batch_uid: UUID,
        parents: Sequence[Item],
    ) -> AnyItem:
        """Construct an unsaved Pydantic ``AnyItem`` for ``item_schema`` with
        relation fields populated from ``parents``. Identifier and name are
        left blank for the factory to fill in.
        """
        attributes = {
            tag: self._attribute_service.empty_attribute_from_schema(schema)
            for tag, schema in item_schema.attributes.items()
        }
        private_attributes = {
            tag: self._attribute_service.empty_attribute_from_schema(schema)
            for tag, schema in item_schema.private_attributes.items()
        }
        if isinstance(item_schema, SampleSchema):
            parents_dict: Dict[UUID, List[UUID]] = {}
            for parent in parents:
                parents_dict.setdefault(parent.schema_uid, []).append(parent.uid)
            return Sample(
                uid=uuid.UUID(int=0),
                identifier="",
                dataset_uid=dataset_uid,
                schema_uid=item_schema.uid,
                batch_uid=batch_uid,
                attributes=attributes,
                private_attributes=private_attributes,
                parents=parents_dict,
            )
        if isinstance(item_schema, ImageSchema):
            samples_dict: Dict[UUID, List[UUID]] = {}
            for parent in parents:
                samples_dict.setdefault(parent.schema_uid, []).append(parent.uid)
            return Image(
                uid=uuid.UUID(int=0),
                identifier="",
                dataset_uid=dataset_uid,
                schema_uid=item_schema.uid,
                batch_uid=batch_uid,
                attributes=attributes,
                private_attributes=private_attributes,
                format=ImageFormat.OTHER_WSI,
                samples=samples_dict,
            )
        if isinstance(item_schema, AnnotationSchema):
            return Annotation(
                uid=uuid.UUID(int=0),
                identifier="",
                dataset_uid=dataset_uid,
                schema_uid=item_schema.uid,
                batch_uid=batch_uid,
                attributes=attributes,
                private_attributes=private_attributes,
                image=(parents[0].schema_uid, parents[0].uid) if parents else None,
            )
        if isinstance(item_schema, ObservationSchema):
            sample_ref = image_ref = annotation_ref = None
            if parents:
                parent = parents[0]
                if isinstance(parent, Sample):
                    sample_ref = (parent.schema_uid, parent.uid)
                elif isinstance(parent, Image):
                    image_ref = (parent.schema_uid, parent.uid)
                elif isinstance(parent, Annotation):
                    annotation_ref = (parent.schema_uid, parent.uid)
            return Observation(
                uid=uuid.UUID(int=0),
                identifier="",
                dataset_uid=dataset_uid,
                schema_uid=item_schema.uid,
                batch_uid=batch_uid,
                attributes=attributes,
                private_attributes=private_attributes,
                sample=sample_ref,
                image=image_ref,
                annotation=annotation_ref,
            )
        raise TypeError(f"Unknown item schema {type(item_schema).__name__}.")

    def _resolve_identifier(self, item: Item, supplied: Optional[str]) -> str:
        if supplied is not None:
            return supplied
        if self._item_naming_factory is not None:
            return self._item_naming_factory.create_identifier(item)
        # No factory wired: include a short uuid suffix so repeated creates
        # don't collide with ``add()``'s identifier-based dedup and silently
        # merge into the first "New X".
        schema = self._schema_service.items.get(item.schema_uid)
        suffix = uuid.uuid4().hex[:8]
        if schema is None:
            return f"New item ({suffix})"
        return f"New {schema.display_name} ({suffix})"

    def _resolve_name(self, item: Item) -> Optional[str]:
        if self._item_naming_factory is None:
            return None
        return self._item_naming_factory.create_name(item)

    def _resolve_pseudonym(self, item: Item) -> Optional[str]:
        if self._pseudonym_factory is None:
            return None
        return self._pseudonym_factory.create_pseudonym(item)

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
        load_relations: bool = False,
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
                load_relations=load_relations,
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
                load_relations=load_relations,
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
                load_relations=load_relations,
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
                load_relations=load_relations,
            )
        else:
            raise TypeError(f"Unknown item type {item_schema}.")

        return items
