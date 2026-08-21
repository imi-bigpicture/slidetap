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

"""Service for accessing schemas."""

from collections.abc import Iterable, Mapping
from functools import cached_property
from itertools import chain
from uuid import UUID

from slidetap.model import (
    AnnotationSchema,
    AttributeSchema,
    DatasetSchema,
    HierarchyLayout,
    HierarchyPanelLayout,
    ImageSchema,
    ImagesLayout,
    ImagesPanelLayout,
    ItemSchema,
    ListAttributeSchema,
    ObjectAttributeSchema,
    ObservationSchema,
    OverviewLayout,
    OverviewPanelLayout,
    ProjectSchema,
    ReviewUnitSchema,
    RootSchema,
    SampleSchema,
    UnionAttributeSchema,
)
from slidetap.model.schema.review_layout import AnyReviewPanelLayout


class SchemaService:
    """Schema service should be used to interface with schemas."""

    def __init__(self, root_schema: RootSchema):
        self._root_schema = root_schema
        self._validate()

    @property
    def root(self) -> RootSchema:
        return self._root_schema

    def get_attributes(self, schema_uid: UUID) -> Iterable[AttributeSchema]:
        return self.attributes.values()

    def get_attribute(self, attribute_schema_uid: UUID) -> AttributeSchema:
        return self.attributes[attribute_schema_uid]

    def get_attribute_by_name(self, attribute_name: str) -> AttributeSchema:
        return self.attributes_by_name[attribute_name]

    def get_private_attribute(self, attribute_schema_uid: UUID) -> AttributeSchema:
        return self.private_attributes[attribute_schema_uid]

    def has_attribute(self, attribute_schema_uid: UUID) -> bool:
        """Whether the loaded schema has an attribute of this uid.

        Uids are regenerated with the model they are declared in, so an
        attribute that is stored somewhere but is not here is one the loaded
        model no longer has, under that uid or at all.
        """
        return (
            attribute_schema_uid in self.attributes
            or attribute_schema_uid in self.private_attributes
        )

    def get_any_attribute(self, attribute_schema_uid: UUID) -> AttributeSchema:
        """Get any attribute schema by UID."""
        if attribute_schema_uid in self.attributes:
            return self.attributes[attribute_schema_uid]
        if attribute_schema_uid in self.private_attributes:
            return self.private_attributes[attribute_schema_uid]
        raise ValueError(f"Attribute schema with UID {attribute_schema_uid} not found.")

    def get_item(self, item_schema_uid: UUID) -> ItemSchema:
        return self.items[item_schema_uid]

    def get_root(self) -> RootSchema:
        return self._root_schema

    def get_overview_layout(self, layout_uid: UUID) -> OverviewLayout | None:
        """An overview layout by uid, wherever it is defined."""
        return self.overview_layouts.get(layout_uid)

    def get_hierarchy_layout(self, layout_uid: UUID) -> HierarchyLayout | None:
        """A hierarchy layout by uid, wherever it is defined."""
        return self.hierarchy_layouts.get(layout_uid)

    def get_images_layout(self, layout_uid: UUID) -> ImagesLayout | None:
        """An images layout by uid, wherever it is defined."""
        return self.images_layouts.get(layout_uid)

    @cached_property
    def images_layouts(self) -> dict[UUID, ImagesLayout]:
        """Every images layout the application defines, as above."""
        return {
            layout.uid: layout
            for layout in chain(
                self._root_schema.images_layouts,
                (
                    panel.layout
                    for panel in self._review_panels
                    if isinstance(panel, ImagesPanelLayout)
                ),
            )
        }

    @cached_property
    def overview_layouts(self) -> dict[UUID, OverviewLayout]:
        """Every overview layout the application defines.

        The root schema lists the ones an item can be opened with; the rest are
        composed into a review tab, and are asked for by the panel showing
        them just the same.
        """
        return {
            layout.uid: layout
            for layout in chain(
                self._root_schema.overview_layouts,
                (
                    panel.layout
                    for panel in self._review_panels
                    if isinstance(panel, OverviewPanelLayout)
                ),
            )
        }

    @cached_property
    def hierarchy_layouts(self) -> dict[UUID, HierarchyLayout]:
        """Every hierarchy layout the application defines, as above."""
        return {
            layout.uid: layout
            for layout in chain(
                self._root_schema.hierarchy_layouts,
                (
                    panel.layout
                    for panel in self._review_panels
                    if isinstance(panel, HierarchyPanelLayout)
                ),
            )
        }

    @property
    def _review_panels(self) -> Iterable[AnyReviewPanelLayout]:
        if self._root_schema.review_unit is None:
            return ()
        return chain.from_iterable(
            tab.panels for tab in self._root_schema.review_unit.layout.tabs
        )

    @cached_property
    def attributes(self) -> dict[UUID, AttributeSchema]:
        attributes: list[AttributeSchema] = []
        for schema in self.project.attributes.values():
            attributes.extend(self._get_recursive_attributes(schema))
        for schema in self.dataset.attributes.values():
            attributes.extend(self._get_recursive_attributes(schema))
        for item in self.items.values():
            for attribute in item.attributes.values():
                attributes.extend(self._get_recursive_attributes(attribute))
        return {attribute.uid: attribute for attribute in attributes}

    @cached_property
    def attributes_by_name(self) -> dict[str, AttributeSchema]:
        attributes: list[AttributeSchema] = []
        for schema in self.project.attributes.values():
            attributes.extend(self._get_recursive_attributes(schema))
        for schema in self.dataset.attributes.values():
            attributes.extend(self._get_recursive_attributes(schema))
        for item in self.items.values():
            for attribute in item.attributes.values():
                attributes.extend(self._get_recursive_attributes(attribute))
        return {attribute.name: attribute for attribute in attributes}

    @cached_property
    def private_attributes(self) -> dict[UUID, AttributeSchema]:
        """Get all private attributes."""
        attributes: list[AttributeSchema] = []
        attributes.extend(self.project.private_attributes.values())
        attributes.extend(self.dataset.private_attributes.values())
        for item in self.items.values():
            attributes.extend(item.private_attributes.values())

        return {attribute.uid: attribute for attribute in attributes}

    @cached_property
    def items(self) -> dict[UUID, ItemSchema]:
        items: Mapping[UUID, ItemSchema] = (
            self.samples | self.images | self.annotations | self.observations
        )
        return dict(items)

    @cached_property
    def samples(self) -> dict[UUID, SampleSchema]:
        return {sample.uid: sample for sample in self._root_schema.samples.values()}

    @cached_property
    def images(self) -> dict[UUID, ImageSchema]:
        return {image.uid: image for image in self._root_schema.images.values()}

    @cached_property
    def annotations(self) -> dict[UUID, AnnotationSchema]:
        return {
            annotation.uid: annotation
            for annotation in self._root_schema.annotations.values()
        }

    @cached_property
    def observations(self) -> dict[UUID, ObservationSchema]:
        return {
            observation.uid: observation
            for observation in self._root_schema.observations.values()
        }

    @property
    def project(self) -> ProjectSchema:
        return self._root_schema.project

    @property
    def dataset(self) -> DatasetSchema:
        return self._root_schema.dataset

    def parent_schema_caps(self, item_schema: ItemSchema) -> Mapping[UUID, int | None]:
        """Map allowed parent-schema UIDs to their max-parent cap.

        Key presence means the parent schema is allowed; ``None`` means no
        per-schema cap (unlimited). Callers use this to reject mismatched
        parent UIDs and excess parents up front instead of letting
        relation validation flag them after the fact.

        The cap is the maximum half of the relation's cardinality — a
        cardinality that permits more than one is uncapped here, and the
        minimum half is left to relation validation, since creating an item
        with too few parents is a state to flag rather than a call to reject.
        The structural single-parent constraint for Observation/Annotation
        (DB single FK) is the caller's concern.
        """
        if isinstance(item_schema, SampleSchema):
            return {
                relation.parent_uid: None if relation.parents.multiple else 1
                for relation in item_schema.parents
            }
        if isinstance(item_schema, ImageSchema):
            return {
                relation.sample_uid: None if relation.samples.multiple else 1
                for relation in item_schema.samples
            }
        if isinstance(item_schema, AnnotationSchema):
            return {relation.image_uid: None for relation in item_schema.images}
        if isinstance(item_schema, ObservationSchema):
            return (
                {relation.sample_uid: None for relation in item_schema.samples}
                | {relation.image_uid: None for relation in item_schema.images}
                | {
                    relation.annotation_uid: None
                    for relation in item_schema.annotations
                }
            )
        return {}

    @property
    def review_unit(self) -> ReviewUnitSchema | None:
        """What a reviewer works through, where anything is reviewed."""
        return self._root_schema.review_unit

    def review_unit_covers(self, item_schema_uid: UUID) -> bool:
        """Whether items of this schema are answered for by the review unit.

        Parameters
        ----------
        item_schema_uid: UUID
            The item schema to ask about. The review unit's own schema is
            covered by it.

        Returns
        -------
        bool
            False for every schema where nothing is reviewed at all.
        """
        return item_schema_uid in self.review_unit_coverage

    @cached_property
    def review_unit_coverage(self) -> frozenset[UUID]:
        """The item schemas the review unit answers for, its own included.

        Resolved by walking up to the review unit rather than by marking the
        way there, which would state a second time what the review unit
        already states, and the two can disagree.

        Done here rather than per item, so that it costs a lookup at runtime.
        """
        unit = self.review_unit
        if unit is None:
            return frozenset()
        return frozenset(
            schema.uid
            for schema in self.items.values()
            if self._is_at_or_under(schema, unit.schema_uid)
        )

    def _is_at_or_under(self, schema: ItemSchema, unit_uid: UUID) -> bool:
        """Whether ``schema`` is the review unit, or hangs under it.

        A sample can have parents of several kinds, so the branches that lead
        nowhere simply end, and ``seen`` keeps a cycle from walking forever.
        """
        seen: set[UUID] = set()
        walking = [schema]
        while walking:
            item = walking.pop()
            if item.uid == unit_uid:
                return True
            if item.uid in seen:
                continue
            seen.add(item.uid)
            walking.extend(self.items[uid] for uid in self._parent_schema_uids(item))
        return False

    @staticmethod
    def _parent_schema_uids(schema: ItemSchema) -> Iterable[UUID]:
        """The schemas an item of this schema can hang under."""
        if isinstance(schema, SampleSchema):
            return (relation.parent_uid for relation in schema.parents)
        if isinstance(schema, ImageSchema):
            return (relation.sample_uid for relation in schema.samples)
        if isinstance(schema, AnnotationSchema):
            return (relation.image_uid for relation in schema.images)
        if isinstance(schema, ObservationSchema):
            return chain(
                (relation.sample_uid for relation in schema.samples),
                (relation.image_uid for relation in schema.images),
                (relation.annotation_uid for relation in schema.annotations),
            )
        return ()

    def get_item_schema_hierarchy_recursive(self, schema: ItemSchema) -> list[UUID]:
        """The schema and everything under it, each above what hangs from it.

        Ordered rather than gathered: a list of schemas to pick from reads as
        the hierarchy it describes only if it is given in that order.
        """
        # Keys of a dict rather than a set: both drop the repeats, only one
        # keeps the order they were first met in.
        schemas: dict[UUID, None] = {}
        self._walk_schema_hierarchy(schema, schemas)
        return list(schemas)

    def _walk_schema_hierarchy(
        self, schema: ItemSchema, seen: dict[UUID, None]
    ) -> None:
        """Add the schema and everything under it to `seen`, in that order.

        Carried between the levels rather than merged after each: a schema that
        can hold its own kind would otherwise be walked forever.
        """
        if schema.uid in seen:
            return
        seen[schema.uid] = None
        for child_uid in self._child_schema_uids(schema):
            child_schema = self.get_item(child_uid)
            if child_schema is not None:
                self._walk_schema_hierarchy(child_schema, seen)

    @staticmethod
    def _child_schema_uids(schema: ItemSchema) -> Iterable[UUID]:
        """The schemas an item of this schema can have hanging under it."""
        if isinstance(schema, SampleSchema):
            return chain(
                (relation.child_uid for relation in schema.children),
                (relation.image_uid for relation in schema.images),
            )
        if isinstance(schema, ImageSchema):
            return (relation.annotation_uid for relation in schema.annotations)
        return ()

    def _get_recursive_attributes(
        self, schema: AttributeSchema
    ) -> Iterable[AttributeSchema]:
        yield schema
        if isinstance(schema, ListAttributeSchema):
            yield from self._get_recursive_attributes(schema.attribute)
        elif isinstance(schema, UnionAttributeSchema):
            for attribute in schema.attributes:
                yield from self._get_recursive_attributes(attribute)
        elif isinstance(schema, ObjectAttributeSchema):
            for attribute in schema.attributes.values():
                yield from self._get_recursive_attributes(attribute)

    def _validate(self):
        """Reject schemas where one UID resolves to two different attribute
        definitions. A UID appearing more than once is tolerated when the
        schemas are field-equal — frozen Pydantic models compare by value,
        so the same attribute exposed in both public and private collections
        is unambiguous."""
        seen: dict[UUID, AttributeSchema] = {}
        for attribute in chain(
            self.attributes.values(), self.private_attributes.values()
        ):
            existing = seen.get(attribute.uid)
            if existing is not None and existing != attribute:
                raise ValueError(
                    f"Conflicting attribute schemas with UID {attribute.uid}: "
                    f"{existing} vs {attribute}"
                )
            seen[attribute.uid] = attribute
