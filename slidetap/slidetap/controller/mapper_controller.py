"""Controller for handling mappers and mappings."""
from uuid import UUID

from flask import Blueprint, current_app, request
from flask.wrappers import Response

from slidetap.controller.controller import Controller
from slidetap.serialization import AttributeSimplifiedModel
from slidetap.serialization import (
    MapperModel,
    MapperSimplifiedModel,
    MappingItemModel,
)
from slidetap.serialization.mapper import MappingItemSimplifiedModel
from slidetap.services import LoginService
from slidetap.services import AttributeService
from slidetap.services import MapperService
from slidetap.services import SchemaService


class MapperController(Controller):
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
        @self.login_service.validate_auth()
        def create_mapper() -> Response:
            current_app.logger.debug("Creating mapper.")
            mapper_data = MapperModel(only=["name", "attribute_schema_uid"]).load(
                request.get_json()
            )
            assert isinstance(mapper_data, dict)
            mapper = self._mapper_service.create_mapper(
                mapper_data["name"], mapper_data["attribute_schema_uid"]
            )
            return self.return_json(MapperModel().dump(mapper))

        @self.blueprint.route("", methods=["GET"])
        @self.login_service.validate_auth()
        def get_all_mappers() -> Response:
            """Return all registered mappers.

            Returns
            ----------
            Response
                Json-response of registered mappers.
            """

            mappers = MapperSimplifiedModel().dump(
                mapper_service.get_all_mappers(), many=True
            )
            return self.return_json(mappers)

        @self.blueprint.route("/<uuid:mapper_uid>", methods=["GET"])
        @self.login_service.validate_auth()
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

            return self.return_json(MapperModel().dump(mapper))

        @self.blueprint.route("/<uuid:mapper_uid>", methods=["DELETE"])
        @self.login_service.validate_auth()
        def delete_mapper(mapper_uid: UUID) -> Response:
            self._mapper_service.delete_mapper(mapper_uid)
            return self.return_ok()

        @self.blueprint.route("/<uuid:mapper_uid>", methods=["POST"])
        @self.login_service.validate_auth()
        def update_mapper(mapper_uid: UUID) -> Response:
            mapper_data = MapperModel(only=["name"]).load(request.get_json())
            assert isinstance(mapper_data, dict)
            mapper = self._mapper_service.update_mapper(mapper_uid, mapper_data["name"])
            return self.return_json(MapperModel().dump(mapper))

        @self.blueprint.route("/<uuid:mapper_uid>/mapping", methods=["GET"])
        @self.login_service.validate_auth()
        def get_mappings(mapper_uid: UUID) -> Response:
            mappings = mapper_service.get_mappings(mapper_uid)
            return self.return_json(
                MappingItemSimplifiedModel().dump(mappings, many=True)
            )

        @self.blueprint.route("/<uuid:mapper_uid>/attributes", methods=["GET"])
        @self.login_service.validate_auth()
        def get_mapping_attributes(mapper_uid: UUID) -> Response:
            mappings = mapper_service.get_mappings(mapper_uid)
            return self.return_json(
                AttributeSimplifiedModel().dump(
                    [mapping.attribute.value for mapping in mappings], many=True
                )
            )

        @self.blueprint.route("/mapping/create", methods=["POST"])
        @self.login_service.validate_auth()
        def create_mapping() -> Response:
            current_app.logger.debug("Creating mapping.")
            mapping_data = MappingItemModel().load(request.get_json())
            assert isinstance(mapping_data, dict)
            expression = mapping_data["expression"]
            mapper_uid = mapping_data["mapper_uid"]
            attribute = mapping_data["attribute"]
            mapping = self._mapper_service.create_mapping(
                mapper_uid, expression, attribute
            )
            return self.return_json(MappingItemModel().dump(mapping))

        @self.blueprint.route("/mapping/<uuid:mapping_uid>", methods=["POST"])
        @self.login_service.validate_auth()
        def update_mapping(mapping_uid: UUID) -> Response:
            current_app.logger.debug(f"Updating mapping {mapping_uid}")
            mapping_data = MappingItemModel().load(request.get_json())
            assert isinstance(mapping_data, dict)
            expression = mapping_data["expression"]
            attribute = mapping_data["attribute"]
            mapping = self._mapper_service.update_mapping(
                mapping_uid, expression, attribute
            )
            return self.return_json(MappingItemModel().dump(mapping))

        @self.blueprint.route("/mapping/<uuid:mapping_uid>", methods=["DELETE"])
        @self.login_service.validate_auth()
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
        @self.login_service.validate_auth()
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
            return self.return_json(MappingItemModel().dump(mapping))

        @self.blueprint.route("/<uuid:mapper_uid>/unmapped", methods=["GET"])
        @self.login_service.validate_auth()
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
