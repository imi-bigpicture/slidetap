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

"""What a curator should know about how an item is exported."""

from enum import Enum

from slidetap.model.base_model import FrozenBaseModel


class ExportNoticeKind(Enum):
    """How an item is exported otherwise than it is stored.

    An item can be exported in more than one of these ways at once, such as a
    specimen moved to another case under a pseudonym of its own, which is then
    a notice of each.
    """

    SPLIT = "split"
    """Exported as several items, such as a case as one case per specimen."""
    REPLACED = "replaced"
    """Exported as another item, with a pseudonym of its own."""
    MOVED = "moved"
    """Exported under another parent than stored, such as another case."""
    RENAMED = "renamed"
    """Exported under another pseudonym than stored."""


class ExportNotice(FrozenBaseModel):
    """One thing a curator should know about how an item is exported."""

    kind: ExportNoticeKind
    """How the item is exported otherwise than stored."""
    message: str
    """What to tell the curator, in the words of the application."""
