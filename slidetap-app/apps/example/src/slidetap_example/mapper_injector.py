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


from typing import Iterable, Tuple
from uuid import uuid4

from slidetap.external_interfaces import MapperInjectorInterface
from slidetap.model import (
    Code,
    CodeAttribute,
    ListAttributeSchema,
    Mapper,
    MapperGroup,
    MappingItem,
)

from slidetap_example.schema import ExampleSchema


class ExampleMapperInjector(MapperInjectorInterface):
    def __init__(self, schema: ExampleSchema):
        self._schema = schema

    def inject(
        self,
    ) -> Iterable[Tuple[MapperGroup, Iterable[Tuple[Mapper, Iterable[MappingItem]]]]]:
        mappers = (
            self._create_collection_mapper(),
            self._create_fixation_mapper(),
            self._create_sampling_method_mapper(),
            self._create_embedding_mapper(),
            self._create_stain_mapper(),
        )
        group = MapperGroup(
            uid=uuid4(),
            name="Example Mappers",
            mappers=[],
            default_enabled=True,
        )
        yield group, mappers

    def _create_collection_mapper(self) -> Tuple[Mapper, Iterable[MappingItem]]:
        collection_schema = self._schema.specimen.attributes["collection"]
        collection_mapper = Mapper(
            uid=uuid4(),
            name="collection",
            attribute_schema_uid=collection_schema.uid,
            root_attribute_schema_uid=collection_schema.uid,
        )
        items = (
            MappingItem(
                uid=uuid4(),
                mapper_uid=collection_mapper.uid,
                expression="Excision",
                attribute=CodeAttribute(
                    uid=uuid4(),
                    schema_uid=collection_schema.uid,
                    original_value=Code(
                        code="Excision", scheme="CUSTOM", meaning="Excision"
                    ),
                    display_value="excision",
                ),
            ),
        )
        return collection_mapper, items

    def _create_fixation_mapper(self) -> Tuple[Mapper, Iterable[MappingItem]]:
        fixation_schema = self._schema.specimen.attributes["fixation"]
        fixation_mapper = Mapper(
            uid=uuid4(),
            name="fixation",
            attribute_schema_uid=fixation_schema.uid,
            root_attribute_schema_uid=fixation_schema.uid,
        )
        items = (
            MappingItem(
                uid=uuid4(),
                mapper_uid=fixation_mapper.uid,
                expression="Neutral Buffered Formalin",
                attribute=CodeAttribute(
                    uid=uuid4(),
                    schema_uid=fixation_schema.uid,
                    original_value=Code(
                        code="Neutral Buffered Formalin",
                        scheme="CUSTOM",
                        meaning="Neutral Buffered Formalin",
                    ),
                    display_value="formalin",
                ),
            ),
        )
        return fixation_mapper, items

    def _create_sampling_method_mapper(self) -> Tuple[Mapper, Iterable[MappingItem]]:
        sampling_method_schema = self._schema.block.attributes["block_sampling"]
        sampling_method_mapper = Mapper(
            uid=uuid4(),
            name="sampling method",
            attribute_schema_uid=sampling_method_schema.uid,
            root_attribute_schema_uid=sampling_method_schema.uid,
        )
        items = (
            MappingItem(
                uid=uuid4(),
                mapper_uid=sampling_method_mapper.uid,
                expression="Dissection",
                attribute=CodeAttribute(
                    uid=uuid4(),
                    schema_uid=sampling_method_schema.uid,
                    original_value=Code(
                        code="Dissection", scheme="CUSTOM", meaning="Dissection"
                    ),
                    display_value="dissection",
                ),
            ),
        )
        return sampling_method_mapper, items

    def _create_embedding_mapper(self) -> Tuple[Mapper, Iterable[MappingItem]]:
        embedding_schema = self._schema.block.attributes["embedding"]
        embedding_mapper = Mapper(
            uid=uuid4(),
            name="embedding",
            attribute_schema_uid=embedding_schema.uid,
            root_attribute_schema_uid=embedding_schema.uid,
        )
        items = (
            MappingItem(
                uid=uuid4(),
                mapper_uid=embedding_mapper.uid,
                expression="Paraffin wax",
                attribute=CodeAttribute(
                    uid=uuid4(),
                    schema_uid=embedding_schema.uid,
                    original_value=Code(
                        code="Paraffin wax", scheme="CUSTOM", meaning="Paraffin wax"
                    ),
                    display_value="paraffin",
                ),
            ),
        )
        return embedding_mapper, items

    def _create_stain_mapper(self) -> Tuple[Mapper, Iterable[MappingItem]]:
        staining_schema = self._schema.slide.attributes["staining"]
        assert isinstance(staining_schema, ListAttributeSchema)
        stain_mapper = Mapper(
            uid=uuid4(),
            name="stain",
            attribute_schema_uid=staining_schema.attribute.uid,
            root_attribute_schema_uid=staining_schema.uid,
        )
        items = (
            MappingItem(
                uid=uuid4(),
                mapper_uid=stain_mapper.uid,
                expression="hematoxylin",
                attribute=CodeAttribute(
                    uid=uuid4(),
                    schema_uid=staining_schema.attribute.uid,
                    original_value=Code(
                        code="hematoxylin", scheme="CUSTOM", meaning="hematoxylin"
                    ),
                    display_value="hematoxylin",
                ),
            ),
            MappingItem(
                uid=uuid4(),
                mapper_uid=stain_mapper.uid,
                expression="water soluble eosin",
                attribute=CodeAttribute(
                    uid=uuid4(),
                    schema_uid=staining_schema.attribute.uid,
                    original_value=Code(
                        code="water soluble eosin",
                        scheme="CUSTOM",
                        meaning="water soluble eosin",
                    ),
                    display_value="eosin",
                ),
            ),
        )
        return stain_mapper, items
