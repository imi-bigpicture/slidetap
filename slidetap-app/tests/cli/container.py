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

"""The container of the application the CLI tests name by SLIDETAP_TASK_APP."""

import os

from dishka import Container, make_container
from slidetap_example import (
    ExampleImagePreProcessor,
    ExampleMapperInjector,
    ExampleMetadataExportInterface,
    ExampleMetadataImportInterface,
)
from slidetap_example.schema import ExampleSchemaInterface

from slidetap import BaseProvider
from slidetap.config import DatabaseConfig
from slidetap.service_provider import ConfigProvider


def create_container() -> Container:
    """Create a container of the example application, reading the database
    from SLIDETAP_DBURI as an application does."""
    base_provider = BaseProvider(
        schema_interface=ExampleSchemaInterface,
        metadata_export_interface=ExampleMetadataExportInterface,
        metadata_import_interface=ExampleMetadataImportInterface,
        mapper_injector=ExampleMapperInjector,
    )
    base_provider.provide(ExampleImagePreProcessor)
    config_provider = ConfigProvider(
        database_config=lambda: DatabaseConfig(os.environ["SLIDETAP_DBURI"], False)
    )
    return make_container(base_provider, config_provider)
