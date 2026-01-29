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
from typing import Callable, Optional, Type, TypeVar

from dishka import Provider, Scope, WithParents

from slidetap.config import (
    CeleryConfig,
    ConfigParser,
    DatabaseConfig,
    DicomizationConfig,
    ImageCacheConfig,
    LoginConfig,
    MapperConfig,
    SlideTapConfig,
    StorageConfig,
)
from slidetap.external_interfaces import (
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
    ItemService,
    MapperService,
    ModelService,
    ProjectService,
    SchemaService,
    StorageService,
    ValidationService,
)
from slidetap.services.tag_service import TagService


class BaseProvider(Provider):
    def __init__(
        self,
        schema_interface: Type[SchemaInterface],
        metadata_import_interface: Callable[..., MetadataImportInterface],
        metadata_export_interface: Callable[..., MetadataExportInterface],
        pseudonym_factory_interface: Callable[
            ..., Optional[PseudonymFactoryInterface]
        ] = lambda: None,
        mapper_injector: Callable[
            ..., Optional[MapperInjectorInterface]
        ] = lambda: None,
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
        self.provide(ProjectService)
        self.provide(SchemaService)
        self.provide(StorageService)
        self.provide(ValidationService)
        self.provide(TagService)
        self.provide(ModelService)
        self.provide(metadata_import_interface, provides=MetadataImportInterface)
        self.provide(metadata_export_interface, provides=MetadataExportInterface)
        self.provide(
            pseudonym_factory_interface,
            provides=Optional[PseudonymFactoryInterface],
        )
        self.provide(mapper_injector, provides=Optional[MapperInjectorInterface])


ConfigType = TypeVar("ConfigType")


class ConfigProvider(Provider):
    def __init__(
        self,
        slidetap_config: Optional[Callable[..., SlideTapConfig]] = None,
        mapper_config: Optional[Callable[..., MapperConfig]] = None,
        login_config: Optional[Callable[..., LoginConfig]] = None,
        database_config: Optional[Callable[..., DatabaseConfig]] = None,
        image_cache_config: Optional[Callable[..., ImageCacheConfig]] = None,
        celery_config: Optional[Callable[..., CeleryConfig]] = None,
        dicomization_config: Optional[Callable[..., DicomizationConfig]] = None,
        storage_config: Optional[Callable[..., StorageConfig]] = None,
    ):

        def select_config(
            override: Optional[Callable[..., ConfigType]],
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
            select_config(celery_config, CeleryConfig.parse),
            provides=CeleryConfig,
        )
        self.provide(
            select_config(dicomization_config, DicomizationConfig.parse),
            provides=DicomizationConfig,
        )
        self.provide(
            select_config(storage_config, StorageConfig.parse),
            provides=StorageConfig,
        )
