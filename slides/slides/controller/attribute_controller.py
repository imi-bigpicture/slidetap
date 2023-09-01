"""Controller for handling attributes."""
from uuid import UUID

from flask import Blueprint, current_app, request
from flask.wrappers import Response

from slides.controller.controller import Controller
from slides.model.mapping import Mapping
from slides.serialization import (
    AttributeSchemaModel,
    AttributeSimplifiedModel,
    MappingModel,
)
from slides.serialization.attribute import AttributeModel
from slides.services import AttributeService, LoginService, MapperService


class AttributeController(Controller):
    """Controller for attributes."""

    def __init__(
        self,
        login_service: LoginService,
        attribute_service: AttributeService,
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
            current_app.logger.debug(f"Create attribute.")
            attribute_schema = attribute_service.get_schema(attribute_schema_uid)
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
            if attribute.mapping_item_uid is None:
                mapping_item = mapper_service.get_mapping_for_attribute(attribute)
            else:
                mapping_item = mapper_service.get_mapping(attribute.mapping_item_uid)
            if mapping_item is None:
                mapping = Mapping(
                    attribute_uid,
                    attribute.mappable_value,
                )
            else:
                mapping = Mapping(
                    attribute_uid,
                    attribute.mappable_value,
                    expression=mapping_item.expression,
                    value_uid=mapping_item.attribute.uid,
                )

            return self.return_json(MappingModel().dump(mapping))

        @self.blueprint.route("/schemas/<uuid:schema_uid>", methods=["GET"])
        def get_schemas(schema_uid: UUID) -> Response:
            schemas = attribute_service.get_schemas(schema_uid)
            return self.return_json(AttributeSchemaModel().dump(schemas, many=True))

        @self.blueprint.route("/schema/<uuid:attribute_schema_uid>", methods=["GET"])
        def get_attributes_for_schema(attribute_schema_uid: UUID) -> Response:
            attribute_schema = attribute_service.get_schema(attribute_schema_uid)
            attributes = attribute_service.get_for_schema(attribute_schema_uid)
            return self.return_json(
                AttributeSimplifiedModel().dump(attributes, many=True)
            )
