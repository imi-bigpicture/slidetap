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

"""Code model for representing coded values."""

from typing import Optional

from slidetap.model.base_model import FrozenBaseModel


class Code(FrozenBaseModel):
    """Represents a coded value with its scheme and meaning."""

    code: str
    scheme: str
    meaning: str
    scheme_version: Optional[str] = None
