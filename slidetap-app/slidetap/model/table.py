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
from typing import Dict, Iterable, Optional, Sequence

from slidetap.model.image_status import ImageStatus


@dataclass
class ColumnSort:
    column: str
    is_attribute: bool
    descending: bool


@dataclass
class TableRequest:
    start: Optional[int] = None
    size: Optional[int] = None
    identifier_filter: Optional[str] = None
    attribute_filters: Optional[Dict[str, str]] = None
    sorting: Optional[Sequence[ColumnSort]] = None
    included: Optional[bool] = None
    valid: Optional[bool] = None
    status_filter: Optional[Iterable[ImageStatus]] = None
