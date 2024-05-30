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


from dataclasses import dataclass
from typing import Sequence
from uuid import UUID


@dataclass(unsafe_hash=True)
class AttributeValidation:
    valid: bool
    uid: UUID
    display_name: str


@dataclass(unsafe_hash=True)
class RelationValidation:
    valid: bool
    uid: UUID
    display_name: str


@dataclass
class ItemValidation:
    valid: bool
    uid: UUID
    display_name: str
    non_valid_attributes: Sequence[AttributeValidation]
    non_valid_relations: Sequence[RelationValidation]


@dataclass
class ProjectValidation:
    valid: bool
    uid: UUID
    non_valid_attributes: Sequence[AttributeValidation]
    non_valid_items: Sequence[ItemValidation]
