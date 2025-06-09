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

"""Controller for handling mappers and mappings."""
from uuid import UUID

from flask import Blueprint, current_app, request
from flask.wrappers import Response

from slidetap.model.mapper import Mapper, MapperGroup, MappingItem
from slidetap.services import (
    AttributeService,
    MapperService,
    SchemaService,
)
from slidetap.web.controller.controller import SecuredController
from slidetap.web.services import LoginService


class MapperController(SecuredController):
    """Controller for mappers."""

    def __init__(
        self,
        login_service: LoginService,
        mapper_service: MapperService,
        attribute_service: AttributeService,
        schema_service: SchemaService,
    ):
        super().__init__(login_service, Blueprint("mapper", __name__))
        self._mapper_service = mapper_service
        self._attribute_service = attribute_service
        self._schema_service = schema_service

        @self.blueprint.route("create", methods=["POST"])
        def create_mapper() -> Response:
            current_app.logger.debug("Creating mapper.")
            mapper = Mapper.model_validate(request.get_json())
            mapper = self._mapper_service.create_mapper(mapper)
            return self.return_json(mapper.model_dump(mode="json", by_alias=True))

        @self.blueprint.route("", methods=["GET"])
        def get_all_mappers() -> Response:
            """Return all registered mappers.

            Returns
            ----------
            Response
                Json-response of registered mappers.
            """

            mappers = mapper_service.get_mappers()
            return self.return_json(
                [mapper.model_dump(mode="json", by_alias=True) for mapper in mappers]
            )

        @self.blueprint.route("/<uuid:mapper_uid>", methods=["GET"])
        def get_mapper(mapper_uid: UUID) -> Response:
            """Return mapper specified by id.

            Parameters
            ----------
            mapper_uid: UUID
                Id of mapper to get.

            Returns
            ----------
            Response
                Json-response of mapper.
            """
            mapper = mapper_service.get_mapper(mapper_uid)
            if mapper is None:
                return self.return_not_found()

            return self.return_json(mapper.model_dump(mode="json", by_alias=True))

        @self.blueprint.route("/<uuid:mapper_uid>", methods=["DELETE"])
        def delete_mapper(mapper_uid: UUID) -> Response:
            self._mapper_service.delete_mapper(mapper_uid)
            return self.return_ok()

        @self.blueprint.route("/<uuid:mapper_uid>", methods=["POST"])
        def update_mapper(mapper_uid: UUID) -> Response:
            mapper = Mapper.model_validate(request.get_json())
            mapper = self._mapper_service.update_mapper(mapper)
            return self.return_json(mapper.model_dump(mode="json", by_alias=True))

        @self.blueprint.route("/<uuid:mapper_uid>/mapping", methods=["GET"])
        def get_mappings(mapper_uid: UUID) -> Response:
            mappings = mapper_service.get_mappings_for_mapper(mapper_uid)
            return self.return_json(
                [mapping.model_dump(mode="json", by_alias=True) for mapping in mappings]
            )

        @self.blueprint.route("/<uuid:mapper_uid>/attributes", methods=["GET"])
        def get_mapping_attributes(mapper_uid: UUID) -> Response:
            mappings = mapper_service.get_mappings_for_mapper(mapper_uid)
            return self.return_json(
                mapping.model_dump(mode="json", by_alias=True) for mapping in mappings
            )

        @self.blueprint.route("/mapping/create", methods=["POST"])
        def create_mapping() -> Response:
            current_app.logger.debug("Creating mapping.")
            mapping = MappingItem.model_validate(request.get_json())
            mapping = self._mapper_service.create_mapping(mapping)
            return self.return_json(mapping.model_dump(mode="json", by_alias=True))

        @self.blueprint.route("/group/create", methods=["POST"])
        def create_mapper_group() -> Response:
            current_app.logger.debug("Creating mapper group.")
            mapper_group = MapperGroup.model_validate(request.get_json())
            assert isinstance(mapper_group, dict)
            name = mapper_group["name"]
            default_enabled = mapper_group.get("default_enabled", False)
            mapping = self._mapper_service.get_or_create_mapper_group(
                name, default_enabled
            )
            return self.return_json(mapping.model_dump(mode="json", by_alias=True))

        @self.blueprint.route("/mapping/<uuid:mapping_uid>", methods=["POST"])
        def update_mapping(mapping_uid: UUID) -> Response:
            current_app.logger.debug(f"Updating mapping {mapping_uid}")
            mapping = MappingItem.model_validate(request.get_json())
            mapping = self._mapper_service.update_mapping(mapping)
            return self.return_json(mapping.model_dump(mode="json", by_alias=True))

        @self.blueprint.route("/mapping/<uuid:mapping_uid>", methods=["DELETE"])
        def delete_mapping(mapping_uid: UUID) -> Response:
            """Delete mapping specified in form to mapper specified by id.

            Parameters
            ----------
            mapper_uid: UUID
                Id of mapper to delete mapping in specified form.

            Returns
            ----------
            Response
                OK-response if OK.
            """
            try:
                mapper = mapper_service.delete_mapping(mapping_uid)
            except ValueError:
                return self.return_bad_request()
            if mapper is None:
                return self.return_not_found()
            return self.return_ok()

        @self.blueprint.route("/mapping/<uuid:mapping_uid>", methods=["GET"])
        def get_mapping(mapping_uid: UUID) -> Response:
            """Return mapping from specified mapper for specified mappable
            value.

            Parameters
            ----------
            mapper_uid: UUID
                Id of mapper to get mapped value from.
            value: str
                Mappable value to get mapped value for.

            Returns
            ----------
            Response
                Json-response of mappers that can map specified tag.
            """
            mapping = self._mapper_service.get_mapping(mapping_uid)
            if mapping is None:
                return self.return_not_found()
            return self.return_json(mapping.model_dump(mode="json", by_alias=True))

        @self.blueprint.route("/<uuid:mapper_uid>/unmapped", methods=["GET"])
        def get_unmapped(mapper_uid: UUID) -> Response:
            """Return unmapped values from specified mapper.

            Parameters
            ----------
            mapper_uid: UUID
                Id of mapper to get unmapped value from.

            Returns
            ----------
            Response
                Json-response of unmapped values.
            """
            raise NotImplementedError()

            # unmapped_values = mapper_service.get_unmapped(mapper_uid)
            # if unmapped_values is None:
            #     return self.return_not_found()
            # return self.return_json(unmapped_values)

        @self.blueprint.route("/groups", methods=["GET"])
        def get_mapper_groups() -> Response:
            """Return all registered mapper groups.

            Returns
            ----------
            Response
                Json-response of registered mapper groups.
            """
            mapper_groups = self._mapper_service.get_all_mapper_groups()
            return self.return_json(
                [
                    mapper_group.model_dump(mode="json", by_alias=True)
                    for mapper_group in mapper_groups
                ]
            )
