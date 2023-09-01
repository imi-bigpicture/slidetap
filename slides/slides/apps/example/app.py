"""Flask app factory for example application."""
from pathlib import Path
from typing import Optional

from flask import Flask

from slides import SlidesAppFactory
from slides.apps.example.image_importer import ExampleImageImporter
from slides.apps.example.json_metadata_exporter import JsonMetadataExporter
from slides.apps.example.metadata_importer import ExampleMetadataImporter
from slides.apps.example.schema import ExampleSchema
from slides.config import Config
from slides.controller.login import BasicAuthLoginController
from slides.database import CodeAttribute, CodeAttributeSchema
from slides.exporter.image.step_image_exporter import (
    CreateThumbnails,
    DicomProcessingStep,
    StepImageExporter,
    StoreProcessingStep,
)
from slides.model.code import Code
from slides.services import JwtLoginService, MapperService
from slides.storage import Storage
from slides.test_classes import TestAuthService


def create_app(config: Optional[Config] = None, with_mappers: bool = True) -> Flask:
    if config is None:
        config = Config()
    storage = Storage(config.SLIDES_STORAGE)
    image_exporter = StepImageExporter(
        storage,
        [
            DicomProcessingStep(),
            CreateThumbnails(),
            StoreProcessingStep(),
        ],
    )
    metadata_exporter = JsonMetadataExporter(storage)
    login_service = JwtLoginService()
    auth_service = TestAuthService()
    login_controller = BasicAuthLoginController(auth_service, login_service)
    image_importer = ExampleImageImporter(
        image_exporter, Path(r"tests\test_data"), ".svs"
    )
    metadata_importer = ExampleMetadataImporter()
    app = SlidesAppFactory.create(
        auth_service,
        login_service,
        login_controller,
        image_importer,
        image_exporter,
        metadata_importer,
        metadata_exporter,
        config,
    )
    if with_mappers:
        add_example_mappers(app)

    return app


def add_example_mappers(app: Flask):
    with app.app_context():
        mapper_service = MapperService()
        schema = ExampleSchema.create()
        collection_schema = CodeAttributeSchema.get(schema, "collection")
        collection_mapper = mapper_service.get_or_create_mapper(
            "collection",
            collection_schema.uid,
        )
        mapper_service.get_or_create_mapping(
            collection_mapper.uid,
            "Excision",
            CodeAttribute(collection_schema, Code("Excision", "CUSTOM", "Excision")),
        )
        fixation_schema = CodeAttributeSchema.get(schema, "fixation")
        fixation_mapper = mapper_service.get_or_create_mapper(
            "fixation", fixation_schema.uid
        )
        mapper_service.get_or_create_mapping(
            fixation_mapper.uid,
            "Neutral Buffered Formalin",
            CodeAttribute(
                fixation_schema,
                Code(
                    "Neutral Buffered Formalin", "CUSTOM", "Neutral Buffered Formalin"
                ),
            ),
        )
        sampling_method_schema = CodeAttributeSchema.get(schema, "block_sampling")
        sampling_method_mapper = mapper_service.get_or_create_mapper(
            "sampling method", sampling_method_schema.uid
        )
        mapper_service.get_or_create_mapping(
            sampling_method_mapper.uid,
            "Dissection",
            CodeAttribute(
                sampling_method_schema,
                Code("Dissection", "CUSTOM", "Dissection"),
            ),
        )
        embedding_schema = CodeAttributeSchema.get(schema, "embedding")
        embedding_mapper = mapper_service.get_or_create_mapper(
            "embedding", embedding_schema.uid
        )
        mapper_service.get_or_create_mapping(
            embedding_mapper.uid,
            "Paraffin wax",
            CodeAttribute(
                embedding_schema,
                Code("Paraffin wax", "CUSTOM", "Paraffin wax"),
            ),
        )
        stain_schema = CodeAttributeSchema.get(schema, "stain")
        stain_mapper = mapper_service.get_or_create_mapper("stain", stain_schema.uid)
        mapper_service.get_or_create_mapping(
            stain_mapper.uid,
            "hematoxylin stain",
            CodeAttribute(
                stain_schema,
                Code("hematoxylin", "CUSTOM", "hematoxylin"),
            ),
        )
        mapper_service.get_or_create_mapping(
            stain_mapper.uid,
            "water soluble eosin stain",
            CodeAttribute(
                stain_schema,
                Code("water soluble eosin", "CUSTOM", "water soluble eosin"),
            ),
        )
