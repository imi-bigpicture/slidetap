#    Copyright 2026 SECTRA AB
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

"""What the metadata export writes for an item and what it is connected to."""

from slidetap.model.base_model import FrozenBaseModel


class ExportPreviewFile(FrozenBaseModel):
    """One file of the metadata export, holding only what it writes for an
    item and what the item is connected to."""

    name: str
    """What the file is called, such as the name the export gives it."""
    content: str
    """What the export writes in it, serialized as the export serializes it."""
