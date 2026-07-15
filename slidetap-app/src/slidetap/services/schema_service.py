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
    ImageSchema,
    ItemSchema,
    ListAttributeSchema,
    ObjectAttributeSchema,
    ObservationSchema,
    ProjectSchema,
    RootSchema,
    SampleSchema,
    UnionAttributeSchema,
)


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

        Only ``SampleToSampleRelation`` carries a ``max_parents`` field
        today; the other relation types are uncapped at the schema level.
        The structural single-parent constraint for Observation/Annotation
        (DB single FK) is the caller's concern.
        """
        if isinstance(item_schema, SampleSchema):
            return {
                relation.parent_uid: relation.max_parents
                for relation in item_schema.parents
            }
        if isinstance(item_schema, ImageSchema):
            return {relation.sample_uid: None for relation in item_schema.samples}
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

    def get_item_schema_hierarchy_recursive(self, schema: ItemSchema) -> set[UUID]:
        """Recursively get item schema hierarchy."""
        schemas = set([schema.uid])

        if isinstance(schema, SampleSchema):
            for child in schema.children:
                child_schema = self.get_item(child.child_uid)
                if child_schema:
                    schemas.update(
                        self.get_item_schema_hierarchy_recursive(child_schema)
                    )
        elif isinstance(schema, AnnotationSchema):
            for image in schema.images:
                image_schema = self.get_item(image.image_uid)
                if image_schema:
                    schemas.update(
                        self.get_item_schema_hierarchy_recursive(
                            image_schema,
                        )
                    )
        elif isinstance(schema, ObservationSchema):
            for sample in schema.samples:
                sample_schema = self.get_item(sample.sample_uid)
                if sample_schema:
                    schemas.update(
                        self.get_item_schema_hierarchy_recursive(sample_schema)
                    )
            for annotation in schema.annotations:
                annotation_schema = self.get_item(annotation.annotation_uid)
                if annotation_schema:
                    schemas.update(
                        self.get_item_schema_hierarchy_recursive(annotation_schema)
                    )
            for image in schema.images:
                image_schema = self.get_item(image.image_uid)
                if image_schema:
                    schemas.add(image_schema.uid)

        return schemas

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
