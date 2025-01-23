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

import dataclasses
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional
from uuid import UUID

from slidetap.model.attribute import Attribute


@dataclass
class Dataset:
    uid: UUID
    name: str
    schema_uid: UUID
    valid_attributes: Optional[bool] = None
    attributes: Dict[str, Attribute] = dataclasses.field(default_factory=dict)


@dataclass
class ImportableDataset:
    uid: UUID
    name: str
    path: Path
