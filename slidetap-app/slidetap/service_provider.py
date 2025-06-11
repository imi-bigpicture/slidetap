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
from typing import Callable, Optional, Type, Union

from dishka import Provider, Scope

from slidetap.config import Config
from slidetap.external_interfaces import (
    ImageExportInterface,
    ImageImportInterface,
    MetadataExportInterface,
    MetadataImportInterface,
)
from slidetap.model import RootSchema
from slidetap.services import (
    AttributeService,
    BatchService,
    DatabaseService,
    DatasetService,
    ImageCache,
    ImageService,
    ItemService,
    MapperInjector,
    MapperService,
    ProjectService,
    SchemaService,
    StorageService,
    ValidationService,
)
from slidetap.task.scheduler import Scheduler
from slidetap.web.services import (
    BasicAuthService,
    ImageExportService,
    ImageImportService,
    LoginService,
    MetadataExportService,
    MetadataImportService,
)


def create_base_service_provider(
    config: Union[Type[Config], Config],
    schema: Union[Type[RootSchema], RootSchema],
    metadata_import_interface: Type[MetadataImportInterface],
    metadata_export_interface: Type[MetadataExportInterface],
) -> Provider:
    """Create a service provider for the application."""
    service_provider = Provider(scope=Scope.APP)
    service_provider.provide(AttributeService)
    service_provider.provide(BatchService)
    service_provider.provide(DatabaseService)
    service_provider.provide(DatasetService)
    service_provider.provide(ItemService)
    service_provider.provide(MapperService)
    service_provider.provide(ProjectService)
    service_provider.provide(SchemaService)
    service_provider.provide(StorageService)
    service_provider.provide(ValidationService)
    if isinstance(config, Config):
        service_provider.provide(lambda: config, provides=type(config))
        service_provider.provide(lambda: config, provides=Config)
    else:
        service_provider.provide(config, provides=Config)
        service_provider.provide(config, provides=config)
    if isinstance(schema, RootSchema):
        service_provider.provide(lambda: schema, provides=type(schema))
        service_provider.provide(lambda: schema, provides=RootSchema)
    else:
        service_provider.provide(schema, provides=RootSchema)
        service_provider.provide(schema, provides=schema)

    service_provider.provide(
        metadata_import_interface, provides=MetadataImportInterface
    )
    service_provider.provide(
        metadata_export_interface, provides=MetadataExportInterface
    )
    return service_provider


def create_task_service_provider(
    config: Union[Type[Config], Config],
    schema: Union[Type[RootSchema], RootSchema],
    metadata_import_interface: Type[MetadataImportInterface],
    metadata_export_interface: Type[MetadataExportInterface],
    image_import_interface: Type[ImageImportInterface],
    image_export_interface: Type[ImageExportInterface],
) -> Provider:
    """Create a service provider for the application."""
    service_provider = create_base_service_provider(
        config, schema, metadata_import_interface, metadata_export_interface
    )
    service_provider.provide(image_import_interface, provides=ImageImportInterface)
    service_provider.provide(image_export_interface, provides=ImageExportInterface)
    return service_provider


def create_web_service_provider(
    config: Union[Type[Config], Config],
    schema: Union[Type[RootSchema], RootSchema],
    metadata_import_interface: Type[MetadataImportInterface],
    metadata_export_interface: Type[MetadataExportInterface],
    auth_service: Callable[..., BasicAuthService],
    mapper_injector: Callable[..., Optional[MapperInjector]] = lambda: None,
) -> Provider:
    """Create a service provider for the application."""
    service_provider = create_base_service_provider(
        config, schema, metadata_import_interface, metadata_export_interface
    )
    service_provider.provide(mapper_injector, provides=Optional[MapperInjector])
    service_provider.provide(auth_service, provides=BasicAuthService)
    service_provider.provide(LoginService)
    service_provider.provide(ImageService)
    service_provider.provide(ImageCache)
    service_provider.provide(Scheduler)
    service_provider.provide(MetadataImportService)
    service_provider.provide(MetadataExportService)
    service_provider.provide(ImageImportService)
    service_provider.provide(ImageExportService)
    return service_provider
