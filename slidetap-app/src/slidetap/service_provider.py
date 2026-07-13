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
from collections.abc import Callable
from typing import TypeVar

from dishka import Provider, Scope, WithParents

from slidetap.config import (
    ConfigParser,
    DatabaseConfig,
    DicomizationConfig,
    ImageCacheConfig,
    LoginConfig,
    MapperConfig,
    SlideTapConfig,
    StorageConfig,
    TaskConfig,
)
from slidetap.external_interfaces import (
    ItemNamingFactoryInterface,
    MapperInjectorInterface,
    MetadataExportInterface,
    MetadataImportInterface,
    PseudonymFactoryInterface,
)
from slidetap.external_interfaces.schema import SchemaInterface
from slidetap.model import RootSchema
from slidetap.services import (
    AttributeService,
    BatchService,
    DatabaseService,
    DatasetService,
    FileOperations,
    ItemService,
    MapperService,
    MetadataSearchItemService,
    ModelService,
    OverviewService,
    ProjectService,
    SchemaService,
    StorageService,
    ValidationService,
)
from slidetap.services.tag_service import TagService


class BaseProvider(Provider):
    def __init__(
        self,
        schema_interface: type[SchemaInterface],
        metadata_import_interface: Callable[..., MetadataImportInterface],
        metadata_export_interface: Callable[..., MetadataExportInterface],
        pseudonym_factory_interface: Callable[
            ..., PseudonymFactoryInterface | None
        ] = lambda: None,
        item_naming_factory_interface: Callable[
            ..., ItemNamingFactoryInterface | None
        ] = lambda: None,
        mapper_injector: Callable[..., MapperInjectorInterface | None] = lambda: None,
    ):
        def _create_schema(factory: SchemaInterface) -> RootSchema:
            return factory.create()

        super().__init__(scope=Scope.APP)

        self.provide(schema_interface, provides=SchemaInterface)
        self.provide(
            _create_schema, provides=WithParents[schema_interface.get_schema_type()]
        )
        self.provide(AttributeService)
        self.provide(BatchService)
        self.provide(DatabaseService)
        self.provide(DatasetService)
        self.provide(ItemService)
        self.provide(MapperService)
        self.provide(MetadataSearchItemService)
        self.provide(OverviewService)
        self.provide(ProjectService)
        self.provide(SchemaService)
        self.provide(FileOperations)
        self.provide(StorageService)
        self.provide(ValidationService)
        self.provide(TagService)
        self.provide(ModelService)
        self.provide(metadata_import_interface, provides=MetadataImportInterface)
        self.provide(metadata_export_interface, provides=MetadataExportInterface)
        self.provide(
            pseudonym_factory_interface,
            provides=PseudonymFactoryInterface | None,
        )
        self.provide(
            item_naming_factory_interface,
            provides=ItemNamingFactoryInterface | None,
        )
        self.provide(mapper_injector, provides=MapperInjectorInterface | None)


ConfigType = TypeVar("ConfigType")


class ConfigProvider(Provider):
    def __init__(
        self,
        slidetap_config: Callable[..., SlideTapConfig] | None = None,
        mapper_config: Callable[..., MapperConfig] | None = None,
        login_config: Callable[..., LoginConfig] | None = None,
        database_config: Callable[..., DatabaseConfig] | None = None,
        image_cache_config: Callable[..., ImageCacheConfig] | None = None,
        task_config: Callable[..., TaskConfig] | None = None,
        dicomization_config: Callable[..., DicomizationConfig] | None = None,
        storage_config: Callable[..., StorageConfig] | None = None,
    ):

        def select_config(
            override: Callable[..., ConfigType] | None,
            default: Callable[..., ConfigType],
        ) -> Callable[..., ConfigType]:
            """If a config instance is provided, return a factory that returns it.
            Otherwise, return the parse function to create the config."""
            if override is not None:
                return override
            return default

        super().__init__(scope=Scope.APP)
        self.provide(ConfigParser.create, provides=ConfigParser)
        self.provide(
            select_config(slidetap_config, SlideTapConfig.parse),
            provides=SlideTapConfig,
        )
        self.provide(
            select_config(mapper_config, MapperConfig.parse),
            provides=MapperConfig,
        )
        self.provide(
            select_config(login_config, LoginConfig.parse),
            provides=LoginConfig,
        )
        self.provide(
            select_config(database_config, DatabaseConfig.parse),
            provides=DatabaseConfig,
        )
        self.provide(
            select_config(image_cache_config, ImageCacheConfig.parse),
            provides=ImageCacheConfig,
        )
        self.provide(
            select_config(task_config, TaskConfig.parse),
            provides=TaskConfig,
        )
        self.provide(
            select_config(dicomization_config, DicomizationConfig.parse),
            provides=DicomizationConfig,
        )
        self.provide(
            select_config(storage_config, StorageConfig.parse),
            provides=StorageConfig,
        )
