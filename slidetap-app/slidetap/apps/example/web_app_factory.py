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

"""FastAPI app factory for example application."""

from typing import Optional

from dishka import make_async_container
from fastapi import FastAPI
from slidetap.apps.example.config import ExampleConfig
from slidetap.apps.example.interfaces import (
    ExampleMetadataExportInterface,
    ExampleMetadataImportInterface,
)
from slidetap.apps.example.interfaces.metadata_import import ExampleImagePreProcessor
from slidetap.apps.example.mapper_injector import ExampleMapperInjector
from slidetap.apps.example.schema import ExampleSchema
from slidetap.service_provider import BaseProvider
from slidetap.web.app_factory import SlideTapWebAppFactory
from slidetap.web.service_provider import WebAppProvider
from slidetap.web.services import HardCodedBasicAuthTestService


def create_app(
    config: Optional[ExampleConfig] = None,
) -> FastAPI:
    if config is None:
        config = ExampleConfig()
    base_provider = BaseProvider[ExampleConfig, ExampleSchema](
        config=config,
        schema=ExampleSchema(),
        metadata_export_interface=ExampleMetadataExportInterface,
        metadata_import_interface=ExampleMetadataImportInterface,
    )
    web_provider = WebAppProvider(
        auth_service=lambda: HardCodedBasicAuthTestService({"test": "test"}),
        mapper_injector=ExampleMapperInjector,
    )
    web_provider.provide(ExampleImagePreProcessor)
    container = make_async_container(base_provider, web_provider)

    return SlideTapWebAppFactory.create(
        config=config,
        container=container,
    )
