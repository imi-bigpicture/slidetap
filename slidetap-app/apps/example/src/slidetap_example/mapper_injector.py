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


import logging
from typing import List
from uuid import uuid4

from slidetap.model import Code, CodeAttribute, ListAttributeSchema, Mapper
from slidetap.services import MapperService
from slidetap.services.mapper_service import MapperInjector

from slidetap_example.schema import ExampleSchema


class ExampleMapperInjector(MapperInjector):
    def __init__(self, schema: ExampleSchema, mapper_service: MapperService):
        self._schema = schema
        self._mapper_service = mapper_service

    def inject(self):
        mappers: List[Mapper] = []
        collection_schema = self._schema.specimen.attributes["collection"]
        collection_mapper = self._mapper_service.get_or_create_mapper(
            "collection",
            collection_schema.uid,
        )
        self._mapper_service.get_or_create_mapping(
            collection_mapper.uid,
            "Excision",
            CodeAttribute(
                uid=uuid4(),
                schema_uid=collection_schema.uid,
                original_value=Code(
                    code="Excision", scheme="CUSTOM", meaning="Excision"
                ),
                display_value="excision",
            ),
        )
        mappers.append(collection_mapper)
        fixation_schema = self._schema.specimen.attributes["fixation"]
        fixation_mapper = self._mapper_service.get_or_create_mapper(
            "fixation", fixation_schema.uid
        )
        self._mapper_service.get_or_create_mapping(
            fixation_mapper.uid,
            "Neutral Buffered Formalin",
            CodeAttribute(
                uid=uuid4(),
                schema_uid=fixation_schema.uid,
                original_value=Code(
                    code="Neutral Buffered Formalin",
                    scheme="CUSTOM",
                    meaning="Neutral Buffered Formalin",
                ),
                display_value="formalin",
            ),
        )
        mappers.append(fixation_mapper)
        sampling_method_schema = self._schema.block.attributes["block_sampling"]
        sampling_method_mapper = self._mapper_service.get_or_create_mapper(
            "sampling method", sampling_method_schema.uid
        )
        self._mapper_service.get_or_create_mapping(
            sampling_method_mapper.uid,
            "Dissection",
            CodeAttribute(
                uid=uuid4(),
                schema_uid=sampling_method_schema.uid,
                original_value=Code(
                    code="Dissection", scheme="CUSTOM", meaning="Dissection"
                ),
                display_value="dissection",
            ),
        )
        mappers.append(sampling_method_mapper)
        embedding_schema = self._schema.block.attributes["embedding"]
        embedding_mapper = self._mapper_service.get_or_create_mapper(
            "embedding", embedding_schema.uid
        )
        self._mapper_service.get_or_create_mapping(
            embedding_mapper.uid,
            "Paraffin wax",
            CodeAttribute(
                uid=uuid4(),
                schema_uid=embedding_schema.uid,
                original_value=Code(
                    code="Paraffin wax", scheme="CUSTOM", meaning="Paraffin wax"
                ),
                display_value="paraffin",
            ),
        )
        mappers.append(embedding_mapper)
        staining_schema = self._schema.slide.attributes["staining"]
        assert isinstance(staining_schema, ListAttributeSchema)
        stain_mapper = self._mapper_service.get_or_create_mapper(
            "stain", staining_schema.attribute.uid, staining_schema.uid
        )
        self._mapper_service.get_or_create_mapping(
            stain_mapper.uid,
            "hematoxylin",
            CodeAttribute(
                uid=uuid4(),
                schema_uid=staining_schema.attribute.uid,
                original_value=Code(
                    code="hematoxylin", scheme="CUSTOM", meaning="hematoxylin"
                ),
                display_value="hematoxylin",
            ),
        )
        self._mapper_service.get_or_create_mapping(
            stain_mapper.uid,
            "water soluble eosin",
            CodeAttribute(
                uid=uuid4(),
                schema_uid=staining_schema.attribute.uid,
                original_value=Code(
                    code="water soluble eosin",
                    scheme="CUSTOM",
                    meaning="water soluble eosin",
                ),
                display_value="eosin",
            ),
        )
        mappers.append(stain_mapper)
        mapper_group = self._mapper_service.get_or_create_mapper_group(
            "Example mappers",
            default_enabled=True,
        )
        logging.info(
            f"Adding mappers {[mapper.name for mapper in mappers]} to group {mapper_group.name} with uid {mapper_group.uid}"
        )
        mapper_group = self._mapper_service.add_mappers_to_group(mapper_group, mappers)
        logging.info(
            f"Mappers in group {mapper_group.name}: {[mapper for mapper in mapper_group.mappers]}, default enabled: {mapper_group.default_enabled}"
        )
