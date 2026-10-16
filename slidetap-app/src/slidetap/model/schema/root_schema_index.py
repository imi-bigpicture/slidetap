#    Copyright 2026 SECTRA AB
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

"""A root schema, and what is looked up within it."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import cached_property
from itertools import chain
from uuid import UUID

from slidetap.model.attribute import AnyAttribute
from slidetap.model.errors import MigrationError
from slidetap.model.schema.attribute_schema import (
    AnyAttributeSchema,
    AttributeSchema,
    ListAttributeSchema,
    ObjectAttributeSchema,
    UnionAttributeSchema,
)
from slidetap.model.schema.dataset_schema import DatasetSchema
from slidetap.model.schema.hierarchy_layout import HierarchyLayout
from slidetap.model.schema.images_layout import ImagesLayout
from slidetap.model.schema.item_schema import (
    AnnotationSchema,
    AnyItemSchema,
    ImageSchema,
    ItemSchema,
    ObservationSchema,
    SampleSchema,
)
from slidetap.model.schema.overview_layout import OverviewLayout
from slidetap.model.schema.project_schema import ProjectSchema
from slidetap.model.schema.review_layout import (
    AnyReviewPanelLayout,
    HierarchyPanelLayout,
    ImagesPanelLayout,
    OverviewPanelLayout,
)
from slidetap.model.schema.review_unit_schema import ReviewUnitSchema
from slidetap.model.schema.root_schema import AnyEntitySchema, RootSchema
from slidetap.model.schema.root_schema_summary import RootSchemaSummary


@dataclass(frozen=True, eq=False)
class RootSchemaIndex:
    """A root schema the application provides, and what is looked up within
    it: what is derived from the schema, and whether it is the root of new
    projects.

    Item schemas and relations are only meaningful within their root: the same
    uid can have a different definition in another root.

    Compared and hashed by identity, rather than by its schema: the lookups
    are cached on it.
    """

    schema: RootSchema

    is_default: bool
    """Whether new projects are created with the root."""

    @property
    def uid(self) -> UUID:
        return self.schema.uid

    @property
    def family_uid(self) -> UUID:
        return self.schema.family_uid

    @property
    def display_name(self) -> str:
        """The name of the root's family, and its version where it has one."""
        if self.schema.version is None:
            return self.schema.name
        return f"{self.schema.name} {self.schema.version}"

    def summary(self) -> RootSchemaSummary:
        """The root without its content, as it is listed."""
        return RootSchemaSummary(
            uid=self.uid,
            name=self.schema.name,
            version=self.schema.version,
            family_uid=self.family_uid,
            new_projects=self.is_default,
        )

    def get_attributes(self) -> Iterable[AnyAttributeSchema]:
        return self.attributes.values()

    def get_attribute_by_name(self, attribute_name: str) -> AttributeSchema:
        return self.attributes_by_name[attribute_name]

    def has_attribute(self, attribute_schema_uid: UUID) -> bool:
        """Whether the root has an attribute schema of this uid, public or
        private."""
        return (
            attribute_schema_uid in self.attributes
            or attribute_schema_uid in self.private_attributes
        )

    def get_item(self, item_schema_uid: UUID) -> AnyItemSchema:
        return self.items[item_schema_uid]

    def get_entity_schema(self, schema_uid: UUID) -> AnyEntitySchema:
        """Get the project, dataset, or item schema of a uid.

        Parameters
        ----------
        schema_uid: UUID
            The uid of the schema.

        Returns
        -------
        AnyEntitySchema
            The schema.

        Raises
        ------
        KeyError
            If the root has no project, dataset, or item schema of the uid.
        """
        if schema_uid == self.project.uid:
            return self.project
        if schema_uid == self.dataset.uid:
            return self.dataset
        return self.items[schema_uid]

    def get_entity_attribute_schema(
        self, entity_schema_uid: UUID, attribute_schema_uid: UUID
    ) -> tuple[str, AttributeSchema]:
        """Get the tag and the top-level attribute schema of a uid in the
        project, dataset, or item schema of a uid, a public or else a private
        attribute.

        Parameters
        ----------
        entity_schema_uid: UUID
            The uid of the project, dataset, or item schema.
        attribute_schema_uid: UUID
            The uid of the attribute schema.

        Returns
        -------
        tuple[str, AttributeSchema]
            The tag and the attribute schema.

        Raises
        ------
        KeyError
            If the root has no project, dataset, or item schema of the uid.
        MigrationError
            If the schema has no top-level attribute of the attribute schema.
        """
        entity_schema = self.get_entity_schema(entity_schema_uid)
        for tag, attribute_schema in (
            *entity_schema.attributes.items(),
            *entity_schema.private_attributes.items(),
        ):
            if attribute_schema.uid == attribute_schema_uid:
                return tag, attribute_schema
        raise MigrationError(
            f"Attribute schema {attribute_schema_uid} is not an attribute of "
            f"schema {entity_schema.uid}."
        )

    @staticmethod
    def refuse_attribute_off_schema(
        entity_uid: UUID,
        tag: str,
        attribute: AnyAttribute,
        schema: AttributeSchema | None,
    ) -> AttributeSchema:
        """Refuse a migrated attribute that is not on the attribute schema of
        its tag.

        Parameters
        ----------
        entity_uid: UUID
            The uid of the project, dataset, or item of the attribute, for the
            error.
        tag: str
            The target tag of the attribute.
        attribute: AnyAttribute
            The attribute.
        schema: AttributeSchema | None
            The attribute schema of the tag in the target schema, or None
            where it has none.

        Returns
        -------
        AttributeSchema
            The attribute schema of the tag.

        Raises
        ------
        MigrationError
            If the target schema has no attribute of the tag, or the attribute
            is on another attribute schema.
        """
        if schema is None or schema.uid != attribute.schema_uid:
            raise MigrationError(
                f"Attribute {attribute.uid} of {entity_uid} is migrated to "
                f"schema {attribute.schema_uid} as {tag!r}, which is not an "
                f"attribute of the target schema."
            )
        return schema

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
        """Every images layout the root defines, as above."""
        return {
            layout.uid: layout
            for layout in chain(
                self.schema.images_layouts,
                (
                    panel.layout
                    for panel in self._review_panels
                    if isinstance(panel, ImagesPanelLayout)
                ),
            )
        }

    @cached_property
    def overview_layouts(self) -> dict[UUID, OverviewLayout]:
        """Every overview layout the root defines.

        The root schema lists the ones an item can be opened with; the rest are
        composed into a review tab, and are asked for by the panel showing
        them just the same.
        """
        return {
            layout.uid: layout
            for layout in chain(
                self.schema.overview_layouts,
                (
                    panel.layout
                    for panel in self._review_panels
                    if isinstance(panel, OverviewPanelLayout)
                ),
            )
        }

    @cached_property
    def hierarchy_layouts(self) -> dict[UUID, HierarchyLayout]:
        """Every hierarchy layout the root defines, as above."""
        return {
            layout.uid: layout
            for layout in chain(
                self.schema.hierarchy_layouts,
                (
                    panel.layout
                    for panel in self._review_panels
                    if isinstance(panel, HierarchyPanelLayout)
                ),
            )
        }

    @property
    def _review_panels(self) -> Iterable[AnyReviewPanelLayout]:
        if self.schema.review_unit is None:
            return ()
        return chain.from_iterable(
            tab.panels for tab in self.schema.review_unit.layout.tabs
        )

    @cached_property
    def attributes(self) -> dict[UUID, AnyAttributeSchema]:
        return {attribute.uid: attribute for attribute in self._iter_attributes()}

    @cached_property
    def attributes_by_name(self) -> dict[str, AnyAttributeSchema]:
        return {attribute.name: attribute for attribute in self._iter_attributes()}

    def _iter_attributes(self) -> Iterable[AnyAttributeSchema]:
        """Every public attribute of the root, nested ones included."""
        for schema in self.project.attributes.values():
            yield from self._get_recursive_attributes(schema)
        for schema in self.dataset.attributes.values():
            yield from self._get_recursive_attributes(schema)
        for item in self.items.values():
            for attribute in item.attributes.values():
                yield from self._get_recursive_attributes(attribute)

    @cached_property
    def private_attributes(self) -> dict[UUID, AnyAttributeSchema]:
        """Get all private attributes."""
        attributes: list[AnyAttributeSchema] = []
        attributes.extend(self.project.private_attributes.values())
        attributes.extend(self.dataset.private_attributes.values())
        for item in self.items.values():
            attributes.extend(item.private_attributes.values())

        return {attribute.uid: attribute for attribute in attributes}

    @cached_property
    def items(self) -> dict[UUID, AnyItemSchema]:
        items: Mapping[UUID, AnyItemSchema] = (
            self.samples | self.images | self.annotations | self.observations
        )
        return dict(items)

    @cached_property
    def samples(self) -> dict[UUID, SampleSchema]:
        return {sample.uid: sample for sample in self.schema.samples.values()}

    @cached_property
    def images(self) -> dict[UUID, ImageSchema]:
        return {image.uid: image for image in self.schema.images.values()}

    @cached_property
    def annotations(self) -> dict[UUID, AnnotationSchema]:
        return {
            annotation.uid: annotation
            for annotation in self.schema.annotations.values()
        }

    @cached_property
    def observations(self) -> dict[UUID, ObservationSchema]:
        return {
            observation.uid: observation
            for observation in self.schema.observations.values()
        }

    @property
    def project(self) -> ProjectSchema:
        return self.schema.project

    @property
    def dataset(self) -> DatasetSchema:
        return self.schema.dataset

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
        return self.schema.review_unit

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
            child_schema = self.items.get(child_uid)
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

    @classmethod
    def _get_recursive_attributes(
        cls, schema: AnyAttributeSchema
    ) -> Iterable[AnyAttributeSchema]:
        yield schema
        if isinstance(schema, ListAttributeSchema):
            yield from cls._get_recursive_attributes(schema.attribute)
        elif isinstance(schema, UnionAttributeSchema):
            for attribute in schema.attributes:
                yield from cls._get_recursive_attributes(attribute)
        elif isinstance(schema, ObjectAttributeSchema):
            for attribute in schema.attributes.values():
                yield from cls._get_recursive_attributes(attribute)

    def validate(self):
        """Reject a root where one item schema UID resolves to two different
        item schemas, such as a sample and an image of the same UID. Item
        schema UIDs are only checked within the root: another root can define
        the same UID differently."""
        seen: dict[UUID, ItemSchema] = {}
        for schema in chain(
            self.schema.samples.values(),
            self.schema.images.values(),
            self.schema.annotations.values(),
            self.schema.observations.values(),
        ):
            existing = seen.get(schema.uid)
            if existing is not None and existing != schema:
                raise ValueError(
                    f"Conflicting item schemas with UID {schema.uid} in root "
                    f"{self.uid}: {existing.name} vs {schema.name}"
                )
            seen[schema.uid] = schema
