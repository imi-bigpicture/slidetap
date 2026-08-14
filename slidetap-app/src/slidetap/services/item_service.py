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
import re
import uuid
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
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
    Annotation,
    AnnotationSchema,
    AnyAttribute,
    AnyItem,
    AttributeFilter,
    AttributeValueLayout,
    Batch,
    ColumnSort,
    GroupedImage,
    Image,
    ImageAttributeLayout,
    ImageFormat,
    ImageGroup,
    ImageSchema,
    ImagesLayout,
    ImageStatus,
    Item,
    ItemIdentity,
    ItemNeighbours,
    ItemSchema,
    Mapper,
    MetadataSearchResult,
    NewChildSuggestion,
    Observation,
    ObservationSchema,
    ReviewQueueItem,
    ReviewStatus,
    Sample,
    SampleSchema,
)
from slidetap.model.hierarchy import HierarchyNode
from slidetap.model.item_select import ItemSelect
from slidetap.model.schema.hierarchy_layout import (
    HierarchyLayout,
    HierarchyLevelLayout,
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
        pseudonym_factory: PseudonymFactoryInterface | None = None,
        item_naming_factory: ItemNamingFactoryInterface | None = None,
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

    def get_optional(self, item_uid: UUID) -> AnyItem | None:
        with self._database_service.get_session() as session:
            item = self._database_service.get_optional_item(session, item_uid)
            return item.model if item is not None else None

    def get_sample(self, item_uid: UUID) -> Sample:
        with self._database_service.get_session() as session:
            return self._database_service.get_sample(session, item_uid).model

    def get_optional_sample(self, item_uid: UUID) -> Sample | None:
        with self._database_service.get_session() as session:
            item = self._database_service.get_optional_sample(session, item_uid)
            return item.model if item is not None else None

    def get_image(self, item_uid: UUID) -> Image:
        with self._database_service.get_session() as session:
            return self._database_service.get_image(session, item_uid).model

    def get_optional_image(self, item_uid: UUID) -> Image | None:
        with self._database_service.get_session() as session:
            item = self._database_service.get_optional_image(session, item_uid)
            return item.model if item is not None else None

    def get_annotation(self, item_uid: UUID) -> Annotation:
        with self._database_service.get_session() as session:
            return self._database_service.get_annotation(session, item_uid).model

    def get_optional_annotation(self, item_uid: UUID) -> Annotation | None:
        with self._database_service.get_session() as session:
            item = self._database_service.get_optional_annotation(session, item_uid)
            return item.model if item is not None else None

    def get_observation(self, item_uid: UUID) -> Observation:
        with self._database_service.get_session() as session:
            return self._database_service.get_observation(session, item_uid).model

    def get_optional_observation(self, item_uid: UUID) -> Observation | None:
        with self._database_service.get_session() as session:
            item = self._database_service.get_optional_observation(session, item_uid)
            return item.model if item is not None else None

    def get_images_for_item(
        self,
        item_uid: UUID,
        group_by_schema_uid: UUID,
        image_schema_uid: UUID | None = None,
        layout: ImagesLayout | None = None,
    ) -> list[ImageGroup]:
        """The images under an item, gathered under what they were made from.

        The layout, where there is one, says what to show beside each group and
        each image; without one they carry their identifiers alone.
        """
        with self._database_service.get_session() as session:
            item = self._database_service.get_item(session, item_uid)
            return [
                self._image_group(group, images, layout)
                for group, images in self._group_images(
                    session, item, group_by_schema_uid, image_schema_uid
                )
            ]

    def _group_images(
        self,
        session: Session,
        item: DatabaseItem,
        group_by_schema_uid: UUID,
        image_schema_uid: UUID | None,
    ) -> list[tuple[DatabaseItem, list[DatabaseImage]]]:
        """What each group stands for, and the images gathered under it."""
        group_by_schema = self._schema_service.get_item(group_by_schema_uid)

        def images_under(sample: DatabaseSample) -> list[DatabaseImage]:
            return list(
                self._database_service.get_sample_images(
                    session, sample, image_schema_uid, recursive=True
                )
            )

        def image_of(image: DatabaseImage | None) -> list[DatabaseImage]:
            """The image where it is one of the kinds asked for, if any."""
            if image is None or (
                image_schema_uid is not None and image.schema_uid != image_schema_uid
            ):
                return []
            return [image]

        if isinstance(item, DatabaseSample):
            if group_by_schema_uid == item.schema_uid:
                return [(item, images_under(item))]
            if isinstance(group_by_schema, SampleSchema):
                return [
                    (group, images_under(group))
                    for group in self._database_service.get_sample_children(
                        session, item, group_by_schema_uid, recursive=True
                    )
                ]
            if isinstance(group_by_schema, ImageSchema):
                return [
                    (image, [image])
                    for image in self._database_service.get_sample_images(
                        session, item, group_by_schema_uid, recursive=True
                    )
                ]

        if isinstance(item, DatabaseImage):
            if group_by_schema_uid != item.schema_uid:
                raise TypeError(
                    f"Cannot group by {group_by_schema} for image {item.uid}."
                )
            return [(item, [item])]

        if isinstance(item, DatabaseAnnotation):
            if group_by_schema_uid == item.schema_uid:
                return [(item, image_of(item.image))]
            if isinstance(group_by_schema, ImageSchema):
                images = image_of(item.image)
                return [(image, [image]) for image in images]

        if isinstance(item, DatabaseObservation):
            if group_by_schema_uid == item.schema_uid:
                return [
                    (
                        item,
                        list(
                            self._database_service.get_observation_images(
                                session, item, image_schema_uid, recursive=True
                            )
                        ),
                    )
                ]
            if isinstance(group_by_schema, ImageSchema):
                images = image_of(item.image)
                return [(image, [image]) for image in images]
            if isinstance(group_by_schema, SampleSchema):
                return [
                    (group, images_under(group))
                    for group in self._database_service.get_observation_samples(
                        session, item, group_by_schema_uid, recursive=True
                    )
                ]
            if isinstance(group_by_schema, AnnotationSchema):
                images = image_of(
                    item.annotation.image if item.annotation is not None else None
                )
                return [(image, [image]) for image in images]

        raise ValueError(
            f"Cannot get images for item {item.uid} with schema {group_by_schema_uid}."
        )

    def _image_group(
        self,
        group: DatabaseItem,
        images: list[DatabaseImage],
        layout: ImagesLayout | None,
    ) -> ImageGroup:
        return ImageGroup(
            identifier=group.identifier,
            name=group.name,
            schema_uid=group.schema_uid,
            label=self._group_label(
                group, layout.group_name_schema_uids if layout is not None else []
            ),
            attributes=self._attributes_in_order(
                group, layout.group_attributes if layout is not None else []
            ),
            images=[
                GroupedImage(
                    image=image.model,
                    attributes=self._image_attributes(
                        image, layout.image_attributes if layout is not None else []
                    ),
                )
                for image in images
            ],
        )

    def _group_label(self, group: DatabaseItem, named_by: Sequence[UUID]) -> str:
        """What to call a group: the items the layout names, or its identifier.

        By name where an item has one, since that is what tells it from its
        siblings — a block is "A", and which specimen it was cut from is what
        the layout asks for beside it.
        """
        if not named_by:
            return group.identifier
        parts: list[str] = []
        for schema_uid in named_by:
            source = (
                group
                if group.schema_uid == schema_uid
                else self._database_service.get_ancestor(group, {schema_uid})
            )
            if source is not None:
                parts.append(source.name or source.identifier)
        return " ".join(parts) if parts else group.identifier

    def _image_attributes(
        self,
        image: DatabaseImage,
        wanted: Sequence[ImageAttributeLayout],
    ) -> dict[str, AnyAttribute]:
        """What to show with an image, read from it or from what it hangs under.

        A stain is recorded on the slide rather than on the picture of it, so an
        attribute may name the kind of item to read it from.
        """
        attributes: dict[str, AnyAttribute] = {}
        for attribute in wanted:
            source: DatabaseItem | None = image
            if attribute.schema_uid is not None:
                source = self._database_service.get_ancestor(
                    image, {attribute.schema_uid}
                )
            if source is None:
                continue
            attributes.update(self._attributes_in_order(source, [attribute]))
        return attributes

    @staticmethod
    def _attributes_in_order(
        item: DatabaseItem, wanted: Sequence[AttributeValueLayout]
    ) -> dict[str, AnyAttribute]:
        """The attributes asked for, in the order they were asked for."""
        by_tag = {attribute.tag: attribute for attribute in item.attributes}
        return {
            attribute.tag: by_tag[attribute.tag].model
            for attribute in wanted
            if attribute.tag in by_tag
        }

    def select(self, item_uid: UUID, value: ItemSelect) -> AnyItem | None:
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

    def set_review_status(
        self,
        item_uid: UUID,
        status: ReviewStatus,
        reason: str | None = None,
        session: Session | None = None,
    ) -> AnyItem | None:
        """Move an item to a review status.

        Reviewing is what clears a flag — there is no separate way to dismiss
        one, since an item that was asked for and then waved through without
        being looked at is the outcome the flag exists to prevent.

        ``reason`` is written only when raising a flag. Reviewing leaves the
        reason in place so what was asked for stays readable next to the answer.
        """
        with self._database_service.get_session(session) as session:
            item = self._database_service.get_optional_item(session, item_uid)
            if item is None:
                return None
            item.review_status = status
            if status == ReviewStatus.FLAGGED:
                item.review_reason = reason
            return item.model

    def flag_for_review(
        self,
        item_uid: UUID,
        reason: str,
        session: Session | None = None,
    ) -> AnyItem | None:
        """Ask for an item to be reviewed, leaving one already flagged alone.

        A second reason would overwrite the first, and the first is the one that
        was there when nobody had looked yet.
        """
        with self._database_service.get_session(session) as session:
            item = self._database_service.get_optional_item(session, item_uid)
            if item is None:
                return None
            if item.review_status == ReviewStatus.FLAGGED:
                return item.model
            item.review_status = ReviewStatus.FLAGGED
            item.review_reason = reason
            return item.model

    def update(self, item: AnyItem) -> AnyItem | None:
        with self._database_service.get_session() as session:
            existing_item = self._database_service.get_optional_item(session, item.uid)
            if existing_item is None:
                return None
            # Read before the edit: only a save that breaks something calls the
            # reviewer back. One that leaves an already-invalid item invalid is
            # somebody working on it, and flagging that would say nothing new.
            was_valid = existing_item.valid
            # Also before: the edit may be the removal of the last link upward,
            # and after it there is no way left to tell what this was part of.
            review_unit = self._review_unit_of(existing_item)
            orphan_holder = self._orphan_holder_of(existing_item)
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
            # Stamped here rather than taken from the item: this is the one
            # path a user's save comes through, and a client that sent its own
            # time would report its clock instead of when the save happened.
            existing_item.last_saved = datetime.now()
            # Parked before validating, so that what is validated is where the
            # image ended up.
            self._park_on_orphan_holder(existing_item, orphan_holder)
            self._validation_service.validate_item_relations(existing_item, session)
            if was_valid and not existing_item.valid and review_unit is not None:
                self.flag_for_review(
                    review_unit.uid,
                    f"{existing_item.identifier} was left invalid by an edit.",
                    session=session,
                )
            return existing_item.model

    def get_hierarchy(
        self, item_uid: UUID, layout: HierarchyLayout
    ) -> HierarchyNode | None:
        """What hangs under an item, nested as it hangs.

        The layout decides how far the tree reaches and what each row says: an
        item of a schema the layout does not name is not shown, and nothing
        under it is either.
        """
        levels = {level.schema_uid: level for level in layout.levels}
        with self._database_service.get_session() as session:
            item = self._database_service.get_optional_item(session, item_uid)
            if item is None:
                return None
            return self._build_hierarchy_node(
                item, orphan=False, ancestors=frozenset(), levels=levels
            )

    def _build_hierarchy_node(
        self,
        item: DatabaseItem,
        orphan: bool,
        ancestors: frozenset[UUID],
        levels: Mapping[UUID, HierarchyLevelLayout],
    ) -> HierarchyNode:
        schema = self._schema_service.items[item.schema_uid]
        level = levels.get(item.schema_uid)
        children = sorted(
            (
                child
                for child in self._database_service.get_children(item)
                if child.uid not in ancestors and child.schema_uid in levels
            ),
            key=self._label_sort_key,
        )
        return HierarchyNode(
            uid=item.uid,
            identifier=item.identifier,
            name=item.name,
            pseudonym=item.pseudonym,
            schema_uid=item.schema_uid,
            schema_display_name=schema.display_name,
            item_value_type=item.item_value_type,
            valid=item.valid,
            orphan=orphan,
            # In the order the layout names them, not the item's: an item holds
            # its attributes in a set, and a row that lists them in a different
            # order from the row above it cannot be read down the column.
            attributes=self._layout_attributes(item, level),
            children=[
                self._build_hierarchy_node(
                    child,
                    self._is_orphan_link(item, child),
                    ancestors | {item.uid},
                    levels,
                )
                for child in children
            ],
        )

    @staticmethod
    def _layout_attributes(
        item: DatabaseItem, level: HierarchyLevelLayout | None
    ) -> dict[str, AnyAttribute]:
        """The attributes the level asks for, in the order it asks for them.

        In the layout's order rather than the item's: an item holds its
        attributes in a set, and a row that lists them in a different order
        from the row above it cannot be read down the column.
        """
        if level is None:
            return {}
        by_tag = {attribute.tag: attribute for attribute in item.attributes}
        return {
            attribute.tag: by_tag[attribute.tag].model
            for attribute in level.attributes
            if attribute.tag in by_tag
        }

    @staticmethod
    def _label_sort_key(item: DatabaseItem) -> list[tuple[int, int, str]]:
        """Order items by what they are called, counting numbers as numbers.

        By the name where there is one, since that is what a tree shows, and
        digit runs compared as values: sorted as text, slide 10 comes between
        1 and 3, which is not an order anyone reads a list in.

        Examples
        --------
        >>> sorted(["10", "3", "1"], key=lambda name: ItemService._label_sort_key(
        ...     type("Item", (), {"name": name, "identifier": name})()
        ... ))
        ['1', '3', '10']
        """
        label = item.name or item.identifier
        return [
            (0, int(part), "") if part.isdigit() else (1, 0, part.lower())
            for part in re.split(r"(\d+)", label)
            if part != ""
        ]

    def _is_orphan_link(self, parent: DatabaseItem, child: DatabaseItem) -> bool:
        """Whether the child hangs under the parent by an orphan relation."""
        if not isinstance(parent, DatabaseSample) or not isinstance(
            child, DatabaseImage
        ):
            return False
        schema = self._schema_service.items[child.schema_uid]
        if not isinstance(schema, ImageSchema):
            return False
        return any(
            relation.orphan and relation.sample_uid == parent.schema_uid
            for relation in schema.samples
        )

    def _review_unit_of(self, item: DatabaseItem) -> DatabaseItem | None:
        """The item that would be reviewed if ``item`` needed a second look.

        The nearest thing above it whose schema declares itself a unit for
        review, or the item itself where its own schema does. Nothing, for an
        item that sits under no such unit.
        """
        unit_schema_uid = self._schema_service.get_review_unit(item.schema_uid)
        if unit_schema_uid is None:
            return None
        if item.schema_uid == unit_schema_uid:
            return item
        return self._database_service.get_ancestor(item, {unit_schema_uid})

    def _orphan_holder_of(self, item: DatabaseItem) -> DatabaseSample | None:
        """Where this image would be parked if it lost the sample it is of.

        The orphan relation names the schema that holds what has nowhere else
        to go; this is the item of that schema the image hangs under now. Read
        before an edit, since the edit may be what cuts the way up to it.
        """
        if not isinstance(item, DatabaseImage):
            return None
        schema = self._schema_service.items[item.schema_uid]
        if not isinstance(schema, ImageSchema):
            return None
        holder_schema_uids = {
            relation.sample_uid for relation in schema.samples if relation.orphan
        }
        if not holder_schema_uids:
            return None
        holder = self._database_service.get_ancestor(item, holder_schema_uids)
        return holder if isinstance(holder, DatabaseSample) else None

    def _park_on_orphan_holder(
        self, item: DatabaseItem, holder: DatabaseSample | None
    ) -> bool:
        """Hang an image that has lost the sample it is of on the orphan
        holder, and say whether it was moved.

        An image with nothing above it is not merely invalid, it is out of
        reach: it appears under nothing, so whoever is sent to look at what it
        was part of has no way to get to it. Parked, it stays invalid, and
        stops being so when somebody puts it on the sample it is really of.

        A link through an orphan relation does not count as somewhere to be, so
        an image already parked, whose sample is then taken away, stays where
        it is.
        """
        if holder is None or not isinstance(item, DatabaseImage):
            return False
        schema = self._schema_service.items[item.schema_uid]
        if not isinstance(schema, ImageSchema):
            return False
        holder_schema_uids = {
            relation.sample_uid for relation in schema.samples if relation.orphan
        }
        if any(
            sample.schema_uid not in holder_schema_uids for sample in item.samples
        ):
            return False
        if holder in item.samples:
            return False
        item.samples = {holder}
        return True

    def add(
        self,
        item: AnyItem,
        mappers: Sequence[DatabaseMapper | Mapper | UUID] | None = None,
        session: Session | None = None,
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
                    self._validation_service.validate_item_relations(
                        existing_item, session
                    )
                self._logger.info(
                    f"Item {item.uid, item.identifier, item.schema_uid} "
                    f"already exists as {existing_item.uid}."
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
            database_item.review_status = item.review_status
            database_item.review_reason = item.review_reason
            self._validation_service.validate_item_attributes(database_item, session)
            self._validation_service.validate_item_pseudonym(database_item, session)
            self._validation_service.validate_item_relations(database_item, session)
            session.flush()
            return database_item.model

    def add_search_result(
        self,
        result: MetadataSearchResult,
        mappers: Sequence[DatabaseMapper | Mapper | UUID] | None = None,
        session: Session | None = None,
    ) -> UUID | None:
        """Add every item from a successful ``MetadataSearchResult`` in
        dependency order and return the entry-level item's DB UID for the
        caller to record with ``mark_complete``.

        Importers that generate fresh UUIDs per run (e.g. ``uuid4`` rather
        than a deterministic hash) hit a failure mode on re-import: when
        an item is deduped by ``(identifier, schema_uid, dataset_uid)`` to
        an existing DB row, that row's UID is returned but the *fresh* UID
        is never inserted. Subsequent items whose parent fields reference
        the fresh UID then fail their strict ``get_sample``/``get_image``/
        ... lookup with ``ValueError: Sample with uid X does not exist``.

        This method maintains a fresh→DB UID remap across the sequence and
        rewrites every item's forward references (Sample.parents,
        Image.samples, Annotation.image, Observation.{sample,image,
        annotation}) before calling :py:meth:`add`. The returned UID is
        ``result.item_uid`` translated through the same remap, so callers
        record the correct entry-level row after dedup.

        Result items must be supplied in dependency order — same contract
        as :py:class:`MetadataSearchResult`.
        """
        with self._database_service.get_session(session) as session:
            uid_remap: dict[UUID, UUID] = {}
            for item in result.items:
                self._remap_item_parent_refs(item, uid_remap)
                db_item = self.add(item, mappers, session=session)
                if db_item.uid != item.uid:
                    uid_remap[item.uid] = db_item.uid
            if result.item_uid is None:
                return None
            return uid_remap.get(result.item_uid, result.item_uid)

    def get_neighbours(
        self,
        item_uid: UUID,
        batch_uid: UUID | None = None,
        pseudonym_mode: bool = False,
    ) -> ItemNeighbours:
        """What comes before and after an item among those of its own kind.

        By identifier, or by pseudonym where that is what is shown: a view of
        one item is stepped through in the order the items are named in, which
        is the order every list of them is read in.

        Within one batch: the lists an item is opened from are a batch's, so
        stepping must not walk out of the batch being worked. The item's own
        batch when the caller does not say which.

        Only the names and the uids are read. Building each sibling in full to
        answer with two uids costs the whole batch's attributes on every item
        opened.
        """

        def name(identifier: str, pseudonym: str | None, uid: UUID) -> str:
            if not pseudonym_mode:
                return identifier
            return pseudonym or f"ANON-{str(uid)[:8].upper()}"

        with self._database_service.get_session() as session:
            item = self._database_service.get_item(session, item_uid)
            siblings = sorted(
                (name(identifier, pseudonym, uid), uid)
                for uid, identifier, pseudonym in self._database_service.get_item_names(
                    session,
                    item.schema_uid,
                    item.dataset_uid,
                    batch_uid or item.batch_uid,
                )
            )
            uids = [uid for _, uid in siblings]
            index = uids.index(item_uid) if item_uid in uids else -1
            return ItemNeighbours(
                previous_uid=uids[index - 1] if index > 0 else None,
                next_uid=uids[index + 1] if -1 < index < len(uids) - 1 else None,
            )

    def get_review_queue(
        self,
        item_schema_uid: UUID,
        dataset_uid: UUID,
        batch_uid: UUID | None = None,
        review_status: ReviewStatus | None = None,
    ) -> list[ReviewQueueItem]:
        """The items of a schema a reviewer works through, and where they stand.

        Without a status this is every item of the schema: a reviewer may want
        to look at something nothing flagged, and needs it in the same list to
        get to it.

        Sorted by identifier so the queue is worked through in a stable order
        rather than in whatever order the database returns.
        """
        with self._database_service.get_session() as session:
            items = self._get_for_schema(
                session,
                item_schema_uid,
                dataset_uid,
                batch_uid,
                review_status=review_status,
            )
            return sorted(
                (
                    ReviewQueueItem(
                        uid=item.uid,
                        identifier=item.identifier,
                        pseudonym=item.pseudonym,
                        review_status=item.review_status,
                        review_reason=item.review_reason,
                        last_saved=item.last_saved,
                    )
                    for item in items
                ),
                key=lambda item: item.identifier,
            )

    def flag_invalid_review_units(
        self,
        dataset_uid: UUID,
        batch_uid: UUID | None = None,
        session: Session | None = None,
    ) -> int:
        """Ask for review of every review unit holding something invalid, and
        return how many were flagged.

        Asked for rather than done on import: an application decides for itself
        when its items are supposed to be valid. One that imports metadata
        first and images after has slides without images for as long as that
        takes, and flagging every case at the end of the metadata import says
        only that the import is not finished yet. Run this once the pieces are
        expected to be in place, and what it finds is what is actually wrong.

        Raising a flag on something already flagged leaves the first reason
        alone, so running it twice does not overwrite what somebody wrote by
        hand.
        """
        flagged = 0
        with self._database_service.get_session(session) as session:
            unit_schemas = [
                schema
                for schema in self._schema_service.items.values()
                if schema.review_unit
            ]
            for schema in unit_schemas:
                units = self._get_for_schema(
                    session, schema.uid, dataset_uid, batch_uid
                )
                for unit in units:
                    items = list(self._database_service.walk_item_descendants(unit))
                    invalid = sorted(
                        item.identifier for item in items if not item.valid
                    )
                    if not invalid:
                        continue
                    shown = ", ".join(invalid[:5])
                    reason = (
                        f"{len(invalid)} of {len(items)} items are not valid: {shown}"
                        f"{', …' if len(invalid) > 5 else ''}"
                    )
                    self.flag_for_review(unit.uid, reason, session=session)
                    flagged += 1
        return flagged

    @staticmethod
    def _remap_item_parent_refs(item: AnyItem, uid_remap: Mapping[UUID, UUID]) -> None:
        """Rewrite ``item``'s forward parent references using ``uid_remap``.

        Covers every relation that ``add_item`` resolves via strict
        ``get_sample``/``get_image``/``get_annotation``/``get_observation``:
        Sample.parents, Image.samples, Annotation.image, and
        Observation.{sample,image,annotation}. Refs not in the remap are
        left untouched.
        """
        if isinstance(item, Sample):
            for schema_uid in list(item.parents.keys()):
                item.parents[schema_uid] = [
                    uid_remap.get(uid, uid) for uid in item.parents[schema_uid]
                ]
        elif isinstance(item, Image):
            for schema_uid in list(item.samples.keys()):
                item.samples[schema_uid] = [
                    uid_remap.get(uid, uid) for uid in item.samples[schema_uid]
                ]
        elif isinstance(item, Annotation):
            if item.image is not None:
                schema_uid, parent_uid = item.image
                item.image = (schema_uid, uid_remap.get(parent_uid, parent_uid))
        elif isinstance(item, Observation):
            if item.sample is not None:
                schema_uid, parent_uid = item.sample
                item.sample = (schema_uid, uid_remap.get(parent_uid, parent_uid))
            if item.image is not None:
                schema_uid, parent_uid = item.image
                item.image = (schema_uid, uid_remap.get(parent_uid, parent_uid))
            if item.annotation is not None:
                schema_uid, parent_uid = item.annotation
                item.annotation = (
                    schema_uid,
                    uid_remap.get(parent_uid, parent_uid),
                )

    def create(
        self,
        item_schema: UUID | ItemSchema,
        batch: UUID | Batch | DatabaseBatch,
        target_parent_uids: Sequence[UUID] | None = None,
        identifier: str | None = None,
        session: Session | None = None,
    ) -> AnyItem | None:
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

    def suggest_child(
        self,
        item_schema: UUID | ItemSchema,
        parent_uid: UUID,
    ) -> NewChildSuggestion:
        """What adding an item of this schema under ``parent_uid`` would do.

        The naming the create would apply, offered before it happens so that
        whoever adds an item is shown the name rather than asked to invent one,
        together with the item already carrying that name where there is one:
        ``add`` hands that one back rather than making another, which amounts
        to a restore where it has been removed from the project. Nothing is
        written; the item is built and thrown away.
        """
        if isinstance(item_schema, UUID):
            item_schema = self._schema_service.items[item_schema]
        with self._database_service.get_session() as session:
            parent = self._database_service.get_item(session, parent_uid)
            new_item = self._build_new_item_model(
                item_schema,
                parent.dataset_uid,
                parent.batch_uid,
                [parent.model],
            )
            identifier = self._resolve_identifier(new_item, None)
            existing = self._database_service.get_optional_item_by_identifier(
                session, identifier, item_schema.uid, parent.dataset_uid
            )
            if existing is None:
                return NewChildSuggestion(identifier=identifier)
            return NewChildSuggestion(
                identifier=identifier,
                existing_uid=existing.uid,
                existing_in_project=existing.selected,
            )

    def get_for_schema(
        self,
        item_schema_uid: UUID,
        dataset_uid: UUID,
        batch_uid: UUID | None = None,
        start: int | None = None,
        size: int | None = None,
        identifier_filter: str | None = None,
        pseudonym_mode: bool = False,
        attribute_filters: Sequence[AttributeFilter] | None = None,
        relation_filters: Iterable[RelationFilter] | None = None,
        tag_filter: Iterable[UUID] | None = None,
        sorting: Iterable[ColumnSort] | None = None,
        selected: bool | None = None,
        valid: bool | None = None,
        review_status: ReviewStatus | None = None,
        status_filter: Iterable[ImageStatus] | None = None,
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
                review_status,
                status_filter,
                load_relations=True,
            )

            return [item.model for item in items]

    def get_identities_for_schema(
        self,
        item_schema_uid: UUID,
        dataset_uid: UUID,
        batch_uid: UUID | None = None,
        start: int | None = None,
        size: int | None = None,
        identifier_filter: str | None = None,
        pseudonym_mode: bool = False,
        attribute_filters: Sequence[AttributeFilter] | None = None,
        relation_filters: Iterable[RelationFilter] | None = None,
        tag_filter: Iterable[UUID] | None = None,
        sorting: Iterable[ColumnSort] | None = None,
        selected: bool | None = None,
        valid: bool | None = None,
        review_status: ReviewStatus | None = None,
        status_filter: Iterable[ImageStatus] | None = None,
    ) -> Iterable[ItemIdentity]:
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
                review_status,
                status_filter,
            )

            return [item.identity for item in items]

    def get_count_for_schema(
        self,
        item_schema_uid: UUID,
        dataset_uid: UUID,
        batch_uid: UUID | None = None,
        identifier_filter: str | None = None,
        pseudonym_mode: bool = False,
        attribute_filters: Sequence[AttributeFilter] | None = None,
        relation_filters: Iterable[RelationFilter] | None = None,
        tag_filter: Iterable[UUID] | None = None,
        selected: bool | None = None,
        valid: bool | None = None,
        review_status: ReviewStatus | None = None,
        status_filter: Iterable[ImageStatus] | None = None,
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
        item: UUID | Item | DatabaseItem,
        value: bool,
        session: Session | None = None,
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
        item: UUID | Item | DatabaseItem,
        target_parent_uids: Sequence[UUID] | None = None,
        identifier: str | None = None,
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

    def move_to_parent(
        self,
        item: UUID | Item | DatabaseItem,
        target_parent_uid: UUID,
        session: Session | None = None,
    ) -> AnyItem:
        """Move an item to another parent, keeping the item itself.

        Unlike ``copy``, nothing is duplicated: the same item, with its
        attributes, private attributes and identifier, ends up under
        ``target_parent_uid``. Used where the data is right but sits on the
        wrong parent — an observation registered against the wrong specimen.
        """
        with self._database_service.get_session(session) as session:
            moved = self._database_service.get_item(session, item)
            item_schema = self._schema_service.items[moved.schema_uid]
            parents = self._validate_target_parents(
                item_schema, [target_parent_uid], session
            )
            parent = parents[0]
            if isinstance(moved, DatabaseObservation):
                moved.sample = self._database_service.get_sample(session, parent.uid)
                moved.image = None
                moved.annotation = None
            elif isinstance(moved, DatabaseAnnotation):
                moved.image = self._database_service.get_image(session, parent.uid)
            elif isinstance(moved, DatabaseSample):
                moved.parents = {self._database_service.get_sample(session, parent.uid)}
            elif isinstance(moved, DatabaseImage):
                moved.samples = {self._database_service.get_sample(session, parent.uid)}
            else:
                raise TypeError(f"Unknown item type {type(moved).__name__}.")
            self._validation_service.validate_item_relations(moved, session)
            return moved.model

    def split_sample(
        self,
        original: UUID | Sample | DatabaseSample,
        splits: Iterable[Mapping[UUID, Sequence[UUID]]],
        batch_uid: UUID | None = None,
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
        target_item_uid: UUID,
        session: Session | None = None,
    ) -> None:
        """Swap a single attribute value between two existing items.

        ``attribute_tag`` may be a top-level tag or a compound
        ``parent.child`` tag pointing at an ObjectAttribute child.

        Only swaps: an item to swap with has to exist already. Creating one
        here used to be supported, but it produced an item with none of the
        source's other attributes — for a diagnosis, everything except the code
        being dragged. Moving the whole item to the other parent is what that
        case actually wants, so use :py:meth:`move_to_parent` for it.
        """
        with self._database_service.get_session(session) as session:
            source = self._database_service.get_item(session, source_item_uid)
            if source is None:
                raise ValueError(f"Source item {source_item_uid} not found")
            target = self._database_service.get_item(session, target_item_uid)
            if target is None:
                raise ValueError(f"Target item {target_item_uid} not found")
            if target.schema_uid != source.schema_uid:
                raise ValueError(
                    f"Cannot swap attribute between items of different "
                    f"schemas (source {source.schema_uid}, target "
                    f"{target.schema_uid})"
                )

            self._attribute_service.swap_attribute_value(source, target, attribute_tag)

            self._validation_service.validate_item_attributes(source, session)
            self._validation_service.validate_item_attributes(target, session)

    def _validate_touched(
        self, touched: Iterable[DatabaseItem], session: Session
    ) -> None:
        """Re-validate every item whose ``selected`` flipped during a
        cascade so ``valid_relations`` reflects the new graph."""
        for touched_item in touched:
            self._validation_service.validate_item_relations(touched_item, session)

    def _mappers_for_item(
        self, item: AnyItem, session: Session
    ) -> list[DatabaseMapper]:
        """Resolve the mappers from every group on the item's batch's project.

        Used by ``add()`` when no explicit mapper list is supplied (e.g.
        the ``POST /api/items/add`` route, which has no batch context of
        its own). Returns ``[]`` for items without a batch.
        """
        if item.batch_uid is None:
            return []
        batch = self._database_service.get_batch(session, item.batch_uid)
        return [
            mapper for group in batch.project.mapper_groups for mapper in group.mappers
        ]

    def _validate_target_parents(
        self,
        item_schema: ItemSchema,
        parent_uids: Sequence[UUID],
        session: Session,
    ) -> list[AnyItem]:
        """Validate parent UIDs against schema constraints and return their
        Pydantic models. Shared by ``create`` and ``copy`` so the rules
        ``allowed parent schemas``, per-schema parent cardinality and the
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
        parents: list[AnyItem] = []
        count_by_parent_schema: dict[UUID, int] = {}
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
            parents_dict: dict[UUID, list[UUID]] = {}
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
            samples_dict: dict[UUID, list[UUID]] = {}
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

    def _resolve_identifier(self, item: Item, supplied: str | None) -> str:
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

    def _resolve_name(self, item: Item) -> str | None:
        if self._item_naming_factory is None:
            return None
        return self._item_naming_factory.create_name(item)

    def _resolve_pseudonym(self, item: Item) -> str | None:
        if self._pseudonym_factory is None:
            return None
        return self._pseudonym_factory.create_pseudonym(item)

    def _select_item(
        self,
        item: UUID | Item | DatabaseItem,
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
        image: UUID | Image | DatabaseImage,
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
        sample: UUID | Sample | DatabaseSample,
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
        observation: UUID | Observation | DatabaseObservation,
        value: bool,
        session: Session,
    ) -> Iterable[DatabaseItem]:
        observation = self._database_service.get_observation(session, observation)
        yield from self._set_selected(observation, value)
        if value:
            yield from self._select_item(observation.item, True, session)

    def _select_annotation(
        self,
        annotation: UUID | Annotation | DatabaseAnnotation,
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
        dataset_uid: UUID | None = None,
        batch_uid: UUID | None = None,
        start: int | None = None,
        size: int | None = None,
        identifier_filter: str | None = None,
        pseudonym_mode: bool = False,
        attribute_filters: Sequence[AttributeFilter] | None = None,
        relation_filters: Iterable[RelationFilter] | None = None,
        tag_filter: Iterable[UUID] | None = None,
        sorting: Iterable[ColumnSort] | None = None,
        selected: bool | None = None,
        valid: bool | None = None,
        review_status: ReviewStatus | None = None,
        status_filter: Iterable[ImageStatus] | None = None,
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
                review_status,
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
                review_status,
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
                review_status,
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
                review_status,
                load_relations=load_relations,
            )
        else:
            raise TypeError(f"Unknown item type {item_schema}.")

        return items
