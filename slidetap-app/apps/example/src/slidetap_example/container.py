#    Copyright 2026 SECTRA AB
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

"""Dependency injection shared by the web app, the task app, and the mapper
set-up of the example application."""

from dishka import Container, Provider, make_container

from slidetap import BaseProvider
from slidetap.service_provider import ConfigProvider
from slidetap_example.config import ExampleConfig
from slidetap_example.interfaces import (
    ExampleImagePreProcessor,
    ExampleMetadataExportInterface,
    ExampleMetadataImportInterface,
)
from slidetap_example.mapper_injector import ExampleMapperInjector
from slidetap_example.schema import ExampleSchemaInterface


def create_providers() -> list[Provider]:
    """Create the providers of the services and configuration the web app, the
    task app, and the mapper set-up share.

    Returns
    -------
    list[Provider]
        The providers.
    """
    base_provider = BaseProvider(
        schema_interface=ExampleSchemaInterface,
        metadata_export_interface=ExampleMetadataExportInterface,
        metadata_import_interface=ExampleMetadataImportInterface,
        mapper_injector=ExampleMapperInjector,
    )
    base_provider.provide(ExampleImagePreProcessor)
    config_provider = ConfigProvider()
    config_provider.provide(ExampleConfig.parse, provides=ExampleConfig)
    return [base_provider, config_provider]


def create_container(*providers: Provider) -> Container:
    """Create the container of the shared services and configuration.

    Parameters
    ----------
    *providers: Provider
        Providers of further services, such as those of the task app.

    Returns
    -------
    Container
        The container.
    """
    return make_container(*create_providers(), *providers)
