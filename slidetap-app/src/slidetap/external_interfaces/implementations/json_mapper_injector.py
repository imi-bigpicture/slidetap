#    Copyright 2025 SECTRA AB
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

"""Service for accessing mappers and mapping items."""

from typing import Iterable, List, Tuple
from uuid import uuid4

from pydantic import RootModel
from slidetap.config import MapperConfig
from slidetap.external_interfaces.mapper_injector import MapperInjectorInterface
from slidetap.model import Mapper, MapperGroup, MappingItem
from slidetap.model.external.mapper import MapperExternal, MapperGroupExternal
from slidetap.services import ModelService, SchemaService


class JsonMapperInjector(MapperInjectorInterface):
    def __init__(
        self,
        config: MapperConfig,
        model_service: ModelService,
        schema_service: SchemaService,
    ):
        self._config = config
        self._model_service = model_service
        self._schema_service = schema_service
        self._root_model = RootModel[List[MapperGroupExternal]]

    def inject(
        self,
    ) -> Iterable[Tuple[MapperGroup, Iterable[Tuple[Mapper, Iterable[MappingItem]]]]]:
        if self._config.mapping_file is None:
            return
        with open(self._config.mapping_file, "r", encoding="utf-8") as file:
            groups = self._root_model.model_validate_json(file.read()).root
        for group in groups:
            yield self._parse_group(group)

    def _parse_group(
        self, group_external: MapperGroupExternal
    ) -> Tuple[MapperGroup, Iterable[Tuple[Mapper, Iterable[MappingItem]]]]:
        group = MapperGroup(
            uid=uuid4(),
            name=group_external.name,
            mappers=[],
            default_enabled=group_external.default_enabled,
        )
        return (
            group,
            (
                self._parse_mapper(mapper_external)
                for mapper_external in group_external.mappers
            ),
        )

    def _parse_mapper(
        self, mapper_external: MapperExternal
    ) -> Tuple[Mapper, Iterable[MappingItem]]:
        schema = self._schema_service.get_attribute_by_name(
            mapper_external.attribute_name
        )
        if mapper_external.root_attribute_name is not None:
            root_schema = self._schema_service.get_attribute_by_name(
                mapper_external.root_attribute_name
            )
        else:
            root_schema = schema
        mapper = Mapper(
            uid=uuid4(),
            name=mapper_external.name,
            attribute_schema_uid=schema.uid,
            root_attribute_schema_uid=root_schema.uid if root_schema else schema.uid,
        )

        return (
            mapper,
            (
                MappingItem(
                    uid=uuid4(),
                    mapper_uid=mapper.uid,
                    expression=expression,
                    attribute=self._model_service.external_attribute_to_attribute(
                        attribute, schema
                    ),
                    hits=0,
                )
                for expression, attribute in mapper_external.items.items()
            ),
        )
