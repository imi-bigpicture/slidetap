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

from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy import JSON, Dialect, TypeDecorator
from sqlalchemy.ext.mutable import MutableDict, MutableList

from slidetap.model import AnyAttribute, Code, Measurement, attribute_factory

ValueType = TypeVar("ValueType")
ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseLoadingJson(TypeDecorator[ValueType], Generic[ValueType, ModelType]):
    """Base class for database types that serialize JSON data using a pydantic model."""

    impl = JSON


class LoadingJson(BaseLoadingJson[ModelType, ModelType]):
    """Database type that serializes JSON data using marschmallow schema."""

    model: type[ModelType]

    def process_bind_param(self, value: ModelType | None, dialect: Dialect):
        if value is None or value == {}:
            return value
        return value.model_dump(mode="json", by_alias=True)

    def process_result_value(self, value, dialect) -> ModelType | None:
        if value is None or value == {}:
            return value
        return self.model.model_validate(value)


class LoadingAttributeJson(BaseLoadingJson[AnyAttribute, AnyAttribute]):
    """JSON column for a single polymorphic attribute, deserialized via
    ``attribute_factory``."""

    def process_bind_param(self, value: AnyAttribute | None, dialect: Dialect):
        if value is None or value == {}:
            return value
        return value.model_dump(mode="json", by_alias=True)

    def process_result_value(self, value, dialect) -> AnyAttribute | None:
        if value is None or value == {}:
            return value
        return attribute_factory(value)


class LoadingAttributeDictJson(BaseLoadingJson[dict[str, AnyAttribute], AnyAttribute]):
    """JSON column for a string-keyed dict of polymorphic attributes."""

    def process_bind_param(
        self, value: dict[str, AnyAttribute] | None, dialect: Dialect
    ):
        if value is None:
            return value
        return {
            key: value.model_dump(mode="json", by_alias=True)
            for key, value in value.items()
        }

    def process_result_value(
        self, value: dict[str, Any] | None, dialect: Dialect
    ) -> dict[str, AnyAttribute] | None:
        if value is None or value == {}:
            return value
        return {key: attribute_factory(value) for key, value in value.items()}


class LoadingAttributeListJson(BaseLoadingJson[list[AnyAttribute], AnyAttribute]):
    """JSON column for a list of polymorphic attributes."""

    def process_bind_param(self, value: list[AnyAttribute] | None, dialect: Dialect):
        if value is None:
            return value
        return [item.model_dump(mode="json", by_alias=True) for item in value]

    def process_result_value(
        self, value: list[Any] | None, dialect: Dialect
    ) -> list[AnyAttribute] | None:
        if value is None or value == {}:
            return value
        return [attribute_factory(item) for item in value]


class MeasurementJson(LoadingJson[Measurement]):
    model = Measurement
    cache_ok = True


class CodeJson(LoadingJson[Code]):
    model = Code
    cache_ok = True


class AttributeJson(LoadingAttributeJson):
    cache_ok = True


class AttributeDictJson(LoadingAttributeDictJson):
    cache_ok = True


class AttributeListJson(LoadingAttributeListJson):
    cache_ok = True


measurement_db_type = MeasurementJson()
"""Database type for (immutable) measurement."""
code_db_type = CodeJson()
"""Database type for (immutable) code."""
attribute_db_type = AttributeJson()
"""Database type for single (immutable) attribute."""
attribute_dict_db_type = MutableDict.as_mutable(AttributeDictJson())
"""Mutable dictionary of (immutable) attributes."""
attribute_list_db_type = MutableList.as_mutable(AttributeListJson())
"""Mutable list of (immutable) attributes."""
