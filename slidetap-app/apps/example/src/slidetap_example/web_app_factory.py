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

from dishka import make_async_container
from fastapi import FastAPI
from slidetap import BaseProvider
from slidetap.external_interfaces.implementations.json_file_auth import (
    JsonFileAuthConfig,
    JsonFileAuthInterface,
)
from slidetap.service_provider import ConfigProvider
from slidetap.web import SlideTapWebAppFactory, WebAppProvider

from slidetap_example import (
    ExampleConfig,
    ExampleImagePreProcessor,
    ExampleMapperInjector,
    ExampleMetadataExportInterface,
    ExampleMetadataImportInterface,
)
from slidetap_example.schema import ExampleSchemaInterface


def create_app() -> FastAPI:
    """Create the FastAPI application with dependency injection."""
    base_provider = BaseProvider(
        schema_interface=ExampleSchemaInterface,
        metadata_export_interface=ExampleMetadataExportInterface,
        metadata_import_interface=ExampleMetadataImportInterface,
        mapper_injector=ExampleMapperInjector,
    )
    config_provider = ConfigProvider()
    config_provider.provide(JsonFileAuthConfig.parse, provides=JsonFileAuthConfig)
    config_provider.provide(ExampleConfig.parse, provides=ExampleConfig)
    web_provider = WebAppProvider(auth_interface=JsonFileAuthInterface)
    web_provider.provide(ExampleImagePreProcessor)
    container = make_async_container(base_provider, config_provider, web_provider)

    return SlideTapWebAppFactory.create(container=container)


app = create_app()
