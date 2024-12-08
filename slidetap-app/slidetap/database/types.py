from typing import Any, Dict, Generic, List, Optional, TypeVar

from flask import current_app
from marshmallow import Schema
from sqlalchemy import JSON, TypeDecorator
from sqlalchemy.ext.mutable import MutableDict, MutableList

from slidetap.model.attribute import Attribute
from slidetap.model.code import Code
from slidetap.model.measurement import Measurement
from slidetap.model.schema.attribute_schema import AttributeSchema
from slidetap.serialization.attribute import AttributeModel
from slidetap.serialization.common import CodeModel, MeasurementModel
from slidetap.serialization.schema.attribute_schema import AttributeSchemaModel

ModelType = TypeVar("ModelType")


class LoadingJson(TypeDecorator, Generic[ModelType]):
    """Database type that serializes JSON data using marschmallow schema."""

    impl = JSON
    schema: Schema
    cache_ok = True

    def process_bind_param(self, value: Optional[ModelType], dialect):
        if value is None or value == {}:
            return value
        return self.schema.dump(value)

    def process_result_value(self, value, dialect) -> Optional[ModelType]:
        if value is None or value == {}:
            return value
        return self.schema.load(value)  # type: ignore


class LoadingDictJson(LoadingJson[Dict[str, ModelType]]):
    """Database type that serializes JSON data using marschmallow schema."""

    def process_bind_param(self, value: Optional[Dict[str, ModelType]], dialect):
        if value is None:
            return value
        return {key: self.schema.dump(value) for key, value in value.items()}

    def process_result_value(
        self, value: Optional[Dict[str, Any]], dialect
    ) -> Optional[Dict[str, ModelType]]:
        if value is None or value == {}:
            return value
        return {key: self.schema.load(value) for key, value in value.items()}  # type: ignore


class LoadingListJson(LoadingJson[List[ModelType]]):
    """Database type that serializes JSON data using marschmallow schema."""

    def process_bind_param(self, value: Optional[List[ModelType]], dialect):
        if value is None:
            return value
        return [self.schema.dump(item) for item in value]

    def process_result_value(
        self, value: Optional[List[Any]], dialect
    ) -> Optional[List[ModelType]]:
        if value is None or value == {}:
            return value
        return [self.schema.load(item) for item in value]  # type: ignore


class MeasurementJson(LoadingJson[Measurement]):
    schema = MeasurementModel()
    cache_ok = True


class CodeJson(LoadingJson[Code]):
    schema = CodeModel()
    cache_ok = True


class AttributeJson(LoadingJson[Attribute]):
    schema = AttributeModel()
    cache_ok = True


class AttributeDictJson(LoadingDictJson[Attribute]):
    schema = AttributeModel()
    cache_ok = True


class AttributeListJson(LoadingListJson[Attribute]):
    schema = AttributeModel()
    cache_ok = True


class AttributeSchemaJson(LoadingJson[AttributeSchema]):
    schema = AttributeSchemaModel()
    cache_ok = True


class AttributeSchemaDictJson(LoadingDictJson[AttributeSchema]):
    schema = AttributeSchemaModel()
    cache_ok = True


class AttributeSchemaListJson(LoadingListJson[AttributeSchema]):
    schema = AttributeSchemaModel()
    cache_ok = True


measurement_db_type = MeasurementJson()
"""Database type for (inmutable) measurement."""
code_db_type = CodeJson()
"""Database type for (inmutable) code."""
attribute_db_type = AttributeJson()
"""Database type for single (inmutable) attribute."""
attribute_dict_db_type = MutableDict.as_mutable(AttributeDictJson())
"""Mutable dictionary of (inmutable) attributes."""
attribute_list_db_type = MutableList.as_mutable(AttributeListJson())
"""Mutable list of (inmutable) attributes."""
attribute_schema_db_type = AttributeSchemaJson()
"""Database type for (inmutable) attribute schema."""
attribute_schema_dict_db_type = MutableDict.as_mutable(AttributeSchemaDictJson())
"""Mutable dictionary of (inmutable) attribute schemas."""
attribute_schema_list_db_type = MutableList.as_mutable(AttributeSchemaListJson())
"""Mutable list of (inmutable) attribute schemas."""
