from functools import cached_property

from slidetap.config import Config
from slidetap.model.schema.root_schema import RootSchema
from slidetap.services import (
    AttributeService,
    BatchService,
    DatabaseService,
    DatasetService,
    ImageService,
    ItemService,
    MapperService,
    ProjectService,
    SchemaService,
    StorageService,
    ValidationService,
)


class ServiceProvider:
    def __init__(
        self,
        config: Config,
        root_schema: RootSchema,
    ):
        self._config = config
        self._root_schema = root_schema

    @cached_property
    def storage_service(self):
        return StorageService(self._config.storage_config)

    @cached_property
    def attribute_service(self):
        return AttributeService(
            schema_service=self.schema_service,
            validation_service=self.validation_service,
            database_service=self.database_service,
        )

    @cached_property
    def batch_service(self):
        return BatchService(
            schema_service=self.schema_service,
            validation_service=self.validation_service,
            database_service=self.database_service,
        )

    @cached_property
    def database_service(self):
        return DatabaseService(database_uri=self._config.database_uri)

    @cached_property
    def dataset_service(self):
        return DatasetService(
            schema_service=self.schema_service,
            validation_service=self.validation_service,
            database_service=self.database_service,
        )

    @cached_property
    def image_service(self):
        return ImageService(
            storage_service=self.storage_service,
            database_service=self.database_service,
        )

    @cached_property
    def item_service(self):
        return ItemService(
            attribute_service=self.attribute_service,
            mapper_service=self.mapper_service,
            schema_service=self.schema_service,
            validation_service=self.validation_service,
            database_service=self.database_service,
        )

    @cached_property
    def mapper_service(self):
        return MapperService(
            validation_service=self.validation_service,
            database_service=self.database_service,
        )

    @cached_property
    def project_service(self):
        return ProjectService(
            attribute_service=self.attribute_service,
            batch_service=self.batch_service,
            schema_service=self.schema_service,
            validation_service=self.validation_service,
            database_service=self.database_service,
            storage_service=self.storage_service,
        )

    @cached_property
    def schema_service(self):
        return SchemaService(self._root_schema)

    @cached_property
    def validation_service(self):
        return ValidationService(
            schema_service=self.schema_service, database_service=self.database_service
        )
