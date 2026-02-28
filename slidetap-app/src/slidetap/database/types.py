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

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from pydantic import BaseModel
from sqlalchemy import JSON, Dialect, TypeDecorator
from sqlalchemy.ext.mutable import MutableDict, MutableList

from slidetap.model import Attribute, Code, Measurement
from slidetap.model.attribute import attribute_factory

ValueType = TypeVar("ValueType")
ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseLoadingJson(TypeDecorator[ValueType], Generic[ValueType, ModelType]):
    """Base class for database types that serialize JSON data using a pydantic model."""

    impl = JSON


class LoadingJson(BaseLoadingJson[ModelType, ModelType]):
    """Database type that serializes JSON data using marschmallow schema."""

    model: Type[ModelType]

    def process_bind_param(self, value: Optional[ModelType], dialect: Dialect):
        if value is None or value == {}:
            return value
        return value.model_dump(mode="json", by_alias=True)

    def process_result_value(self, value, dialect) -> Optional[ModelType]:
        if value is None or value == {}:
            return value
        return self.model.model_validate(value)  # type: ignore


class LoadingUnionJson(BaseLoadingJson[ModelType, ModelType]):
    """Database type that serializes JSON data using marschmallow schema."""

    def process_bind_param(self, value: Optional[ModelType], dialect: Dialect):
        if value is None or value == {}:
            return value
        return value.model_dump(mode="json", by_alias=True)

    def process_result_value(self, value, dialect) -> Optional[ModelType]:
        if value is None or value == {}:
            return value
        return attribute_factory(value)  # type: ignore


class LoadingDictJson(BaseLoadingJson[Dict[str, ModelType], ModelType]):
    """Database type that serializes JSON data using marschmallow schema."""

    def process_bind_param(
        self, value: Optional[Dict[str, ModelType]], dialect: Dialect
    ):
        if value is None:
            return value
        return {
            key: value.model_dump(mode="json", by_alias=True)
            for key, value in value.items()
        }

    def process_result_value(
        self, value: Optional[Dict[str, Any]], dialect: Dialect
    ) -> Optional[Dict[str, ModelType]]:
        if value is None or value == {}:
            return value
        return {key: attribute_factory(value) for key, value in value.items()}  # type: ignore


class LoadingListJson(BaseLoadingJson[List[ModelType], ModelType]):
    """Database type that serializes JSON data using marschmallow schema."""

    def process_bind_param(self, value: Optional[List[ModelType]], dialect: Dialect):
        if value is None:
            return value
        return [item.model_dump(mode="json", by_alias=True) for item in value]

    def process_result_value(
        self, value: Optional[List[Any]], dialect: Dialect
    ) -> Optional[List[ModelType]]:
        if value is None or value == {}:
            return value
        return [attribute_factory(item) for item in value]  # type: ignore


class MeasurementJson(LoadingJson[Measurement]):
    model = Measurement
    cache_ok = True


class CodeJson(LoadingJson[Code]):
    model = Code
    cache_ok = True


class AttributeJson(LoadingUnionJson[Attribute]):
    cache_ok = True


class AttributeDictJson(LoadingDictJson[Attribute]):
    cache_ok = True


class AttributeListJson(LoadingListJson[Attribute]):
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
