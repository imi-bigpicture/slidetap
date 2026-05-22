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

"""Json exporter for metadata."""

from collections.abc import Iterable, Mapping
from typing import Any

from slidetap.model import Item, item_factory
from slidetap.model.project import Project


class JsonMetadataSerializer:
    def serialize_items(self, items: Iterable[Item]) -> list[Mapping[str, Any]]:
        return [self.serialize_item(item) for item in items]

    def serialize_item(self, item: Item) -> Mapping[str, Any]:
        exclude = {
            "selected",
            "dataset_uid",
            "batch_uid",
            "schema_uid",
            "item_value_type",
            "attributes.uid",
            "attributes.display_value",
            "attributes.mappable_value",
            "attributes.schema_uid",
            "attributes.valid",
            "attributes.mapping_item_uid",
            "valid",
            "valid_attributes",
            "valid_relations",
            "private_attributes",
        }
        return item.model_dump(exclude=exclude, mode="json")

    def deserialize_project(self, data: dict[str, Any]) -> Project:
        return Project.model_validate(data)

    def deserialize_items(self, data: Iterable[dict[str, Any]]):
        return [item_factory(item) for item in data]

    def deserialize_item(self, data: dict[str, Any]):
        return item_factory(data)
