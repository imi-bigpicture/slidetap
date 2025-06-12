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
from typing import Callable, Generic, Type, TypeVar, Union

from dishka import Provider, Scope, provide

from slidetap.config import Config, DatabaseConfig, ImageCacheConfig, StorageConfig
from slidetap.external_interfaces import (
    MetadataExportInterface,
    MetadataImportInterface,
)
from slidetap.model import RootSchema
from slidetap.services import (
    AttributeService,
    BatchService,
    DatabaseService,
    DatasetService,
    ItemService,
    MapperService,
    ProjectService,
    SchemaService,
    StorageService,
    ValidationService,
)

InjectType = TypeVar("InjectType")

CallableOrType = Union[Callable[..., InjectType], Type[InjectType]]
InstanceOrCallableOrType = Union[InjectType, Callable[..., InjectType]]

ConfigType = TypeVar("ConfigType", bound=Config)
SchemaType = TypeVar("SchemaType", bound=RootSchema)


class BaseProvider(Provider, Generic[ConfigType, SchemaType]):
    def __init__(
        self,
        config: ConfigType,
        schema: SchemaType,
        metadata_import_interface: CallableOrType[MetadataImportInterface],
        metadata_export_interface: CallableOrType[MetadataExportInterface],
    ):
        super().__init__(scope=Scope.APP)
        self._config = config
        self._schema = schema
        self.provide(lambda: self._config, provides=type(config))
        self.provide(lambda: self._config, provides=Config)
        self.provide(lambda: self._schema, provides=type(schema))
        self.provide(lambda: self._schema, provides=RootSchema)
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
        self.provide(metadata_import_interface, provides=MetadataImportInterface)
        self.provide(metadata_export_interface, provides=MetadataExportInterface)

    @provide
    def storage_config(self) -> StorageConfig:
        """Provide the storage configuration."""
        return self._config.storage_config

    @provide
    def database_config(self) -> DatabaseConfig:
        """Provide the database configuration."""
        return self._config.database_config

    @provide
    def image_cache_config(self) -> ImageCacheConfig:
        """Provide the image cache configuration."""
        return self._config.image_cache_config
