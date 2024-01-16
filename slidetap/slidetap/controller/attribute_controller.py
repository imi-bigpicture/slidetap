"""Controller for handling attributes."""
from uuid import UUID

from flask import Blueprint, current_app, request
from flask.wrappers import Response

from slidetap.controller.controller import SecuredController
from slidetap.serialization.attribute import AttributeModel
from slidetap.serialization.mapper import MappingItemModel
from slidetap.services import AttributeService, LoginService, MapperService
from slidetap.services.schema_service import SchemaService


class AttributeController(SecuredController):
    """Controller for attributes."""

    def __init__(
        self,
        login_service: LoginService,
        attribute_service: AttributeService,
        schema_service: SchemaService,
        mapper_service: MapperService,
    ):
        super().__init__(login_service, Blueprint("attribute", __name__))

        @self.blueprint.route(
            "/<uuid:attribute_uid>",
            methods=["GET"],
        )
        def get_attribute(attribute_uid: UUID) -> Response:
            """
            Parameters
            ----------
            attribute_uid: UUID


            Returns
            ----------
            Response
            """
            current_app.logger.debug(f"Get attribute {attribute_uid}.")
            attribute = attribute_service.get(attribute_uid)
            if attribute is None:
                current_app.logger.error(f"Attribute {attribute_uid} not found.")
                return self.return_not_found()
            # TODO should we map here?
            if attribute.value is None and attribute.mappable_value is not None:
                mapper_service.map(attribute)
            return self.return_json(AttributeModel().dump(attribute))

        @self.blueprint.route(
            "/<uuid:attribute_uid>/update",
            methods=["POST"],
        )
        def update_attribute(attribute_uid: UUID) -> Response:
            """
            Parameters
            ----------
            attribute_uid: UUID


            Returns
            ----------
            Response
            """
            current_app.logger.debug(f"Update attribute {attribute_uid}.")
            attribute = attribute_service.get(attribute_uid)
            if attribute is None:
                current_app.logger.error(f"Attribute {attribute_uid} not found.")
                return self.return_not_found()
            update = AttributeModel().load(request.get_json())
            assert isinstance(update, dict)
            attribute_service.update(attribute, update)
            return self.return_ok()

        @self.blueprint.route(
            "/create/<uuid:attribute_schema_uid>",
            methods=["POST"],
        )
        def create_attribute(attribute_schema_uid: UUID) -> Response:
            """
            Parameters
            ----------
            attribute_uid: UUID


            Returns
            ----------
            Response
            """
            current_app.logger.debug("Create attribute.")
            attribute_schema = schema_service.get_attribute(attribute_schema_uid)
            assert attribute_schema is not None
            attribute_data = AttributeModel(exclude="uid").load(request.get_json())
            assert isinstance(attribute_data, dict)
            attribute = attribute_service.create(attribute_schema, attribute_data)
            return self.return_json(AttributeModel().dump(attribute))

        @self.blueprint.route(
            "/<uuid:attribute_uid>/mapping",
            methods=["GET"],
        )
        def get_mapping(attribute_uid: UUID) -> Response:
            current_app.logger.debug(f"Get mapping for attribute {attribute_uid}.")
            attribute = attribute_service.get(attribute_uid)
            if attribute is None or attribute.mappable_value is None:
                return self.return_not_found()
            if attribute.mapping is None:
                mapping_item = mapper_service.get_mapping_for_attribute(attribute)
            else:
                mapping_item = attribute.mapping
            return self.return_json(MappingItemModel().dump(mapping_item))

        @self.blueprint.route("/schema/<uuid:attribute_schema_uid>", methods=["GET"])
        def get_attributes_for_schema(attribute_schema_uid: UUID) -> Response:
            attributes = attribute_service.get_for_schema(attribute_schema_uid)
            return self.return_json(AttributeModel().dump(attributes, many=True))

        @self.blueprint.route(
            "/<uuid:attribute_uid>/validation",
            methods=["GET"],
        )
        def get_attribute_validation(attribute_uid: UUID) -> Response:
            """Get validation of attribute.

            Parameters
            ----------
            attribute_uid: UUID
                Id of attribute to get validation of.

            Returns
            ----------
            Response
                OK if successful.
            """
            current_app.logger.debug(f"Get validation of attribute {attribute_uid}.")
            is_valid = attribute_service.validate(attribute_uid)
            return self.return_json({"is_valid": is_valid})
