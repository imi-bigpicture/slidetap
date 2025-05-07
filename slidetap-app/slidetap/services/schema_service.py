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

from functools import cached_property
from typing import Dict, Iterable, List, Mapping
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

    @property
    def root(self) -> RootSchema:
        return self._root_schema

    def get_attributes(self, schema_uid: UUID) -> Iterable[AttributeSchema]:
        return self.attributes.values()

    def get_attribute(self, attribute_schema_uid: UUID) -> AttributeSchema:
        return self.attributes[attribute_schema_uid]

    def get_item(self, item_schema_uid: UUID) -> ItemSchema:
        return self.items[item_schema_uid]

    def get_root(self) -> RootSchema:
        return self._root_schema

    @cached_property
    def attributes(self) -> Dict[UUID, AttributeSchema]:
        attributes: List[AttributeSchema] = []
        for schema in self.project.attributes.values():
            attributes.extend(self._get_recusive_attributs(schema))
        for schema in self.dataset.attributes.values():
            attributes.extend(self._get_recusive_attributs(schema))
        for item in self.items.values():
            for attribute in item.attributes.values():
                attributes.extend(self._get_recusive_attributs(attribute))
        return {attribute.uid: attribute for attribute in attributes}

    @cached_property
    def items(self) -> Dict[UUID, ItemSchema]:
        items: Mapping[UUID, ItemSchema] = (
            self.samples | self.images | self.annotations | self.observations
        )
        return dict(items)

    @cached_property
    def samples(self) -> Dict[UUID, SampleSchema]:
        return {sample.uid: sample for sample in self._root_schema.samples.values()}

    @cached_property
    def images(self) -> Dict[UUID, ImageSchema]:
        return {image.uid: image for image in self._root_schema.images.values()}

    @cached_property
    def annotations(self) -> Dict[UUID, AnnotationSchema]:
        return {
            annotation.uid: annotation
            for annotation in self._root_schema.annotations.values()
        }

    @cached_property
    def observations(self) -> Dict[UUID, ObservationSchema]:
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

    def _get_recusive_attributs(
        self, schema: AttributeSchema
    ) -> Iterable[AttributeSchema]:
        yield schema
        if isinstance(schema, ListAttributeSchema):
            yield from self._get_recusive_attributs(schema.attribute)
        elif isinstance(schema, UnionAttributeSchema):
            for attribute in schema.attributes:
                yield from self._get_recusive_attributs(attribute)
        elif isinstance(schema, ObjectAttributeSchema):
            for attribute in schema.attributes.values():
                yield from self._get_recusive_attributs(attribute)
