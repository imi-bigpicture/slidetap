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

"""Flask app factory for example application."""

from pathlib import Path
from typing import Optional, Sequence

from flask import Flask
from slidetap.apps.example.image_importer import ExampleImageImporter
from slidetap.apps.example.json_metadata_exporter import JsonMetadataExporter
from slidetap.apps.example.metadata_importer import ExampleMetadataImporter
from slidetap.apps.example.schema import ExampleSchema
from slidetap.config import Config
from slidetap.controller.login import BasicAuthLoginController
from slidetap.database import CodeAttribute, CodeAttributeSchema
from slidetap.exporter.image import StepImageProcessingExporter
from slidetap.image_processing import (
    CreateThumbnails,
    DicomProcessingStep,
    StoreProcessingStep,
)
from slidetap.image_processing.image_processing_step import FinishingStep
from slidetap.image_processing.step_image_processor import ImagePreProcessor
from slidetap.model.code import Code
from slidetap.scheduler import Scheduler
from slidetap.services import JwtLoginService, MapperService
from slidetap.slidetap import SlideTapAppFactory
from slidetap.storage import Storage
from slidetap.test_classes import AuthTestService


def create_app(
    config: Optional[Config] = None, with_mappers: Optional[Sequence[str]] = None
) -> Flask:
    if config is None:
        config = Config()
    storage = Storage(config.SLIDETAP_STORAGE)
    scheduler = Scheduler(
        config.SLIDETAP_DEFAULT_QUEUE_WORKERS, config.SLIDETAP_HIGH_QUEUE_WORKERS
    )
    image_exporter = StepImageProcessingExporter(
        scheduler,
        storage,
        [
            DicomProcessingStep(use_pseudonyms=False),
            CreateThumbnails(use_pseudonyms=False),
            StoreProcessingStep(use_pseudonyms=False),
            FinishingStep(),
        ],
    )
    metadata_exporter = JsonMetadataExporter(scheduler, storage)
    login_service = JwtLoginService()
    auth_service = AuthTestService()
    login_controller = BasicAuthLoginController(auth_service, login_service)
    image_importer = ExampleImageImporter(
        scheduler,
        ImagePreProcessor(storage),
        Path(r"tests\test_data"),
        ".svs",
    )
    metadata_importer = ExampleMetadataImporter(scheduler)
    app = SlideTapAppFactory.create(
        auth_service,
        login_service,
        login_controller,
        image_importer,
        image_exporter,
        metadata_importer,
        metadata_exporter,
        config,
    )
    add_example_mappers(app, with_mappers)

    return app


def add_example_mappers(app: Flask, with_mappers: Optional[Sequence[str]] = None):
    with app.app_context():
        mapper_service = MapperService()
        schema = ExampleSchema.create()
        if with_mappers is None or "collection" in with_mappers:
            collection_schema = CodeAttributeSchema.get(schema, "collection")
            collection_mapper = mapper_service.get_or_create_mapper(
                "collection",
                collection_schema.uid,
            )
            mapper_service.get_or_create_mapping(
                collection_mapper.uid,
                "Excision",
                CodeAttribute(
                    collection_schema, Code("Excision", "CUSTOM", "Excision")
                ),
            )
        if with_mappers is None or "fixation" in with_mappers:
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
                        "Neutral Buffered Formalin",
                        "CUSTOM",
                        "Neutral Buffered Formalin",
                    ),
                ),
            )
        if with_mappers is None or "block_sampling" in with_mappers:
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
        if with_mappers is None or "embedding" in with_mappers:
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
        if with_mappers is None or "stain" in with_mappers:
            stain_schema = CodeAttributeSchema.get(schema, "stain")
            stain_mapper = mapper_service.get_or_create_mapper(
                "stain", stain_schema.uid
            )
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
