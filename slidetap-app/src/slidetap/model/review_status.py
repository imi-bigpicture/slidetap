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

"""Where an item stands in review."""

from enum import Enum


class ReviewStatus(Enum):
    """Whether an item has been looked at, and whether something asked for it.

    One value rather than a flagged and a reviewed boolean: an item leaves
    ``FLAGGED`` only by being reviewed, so "flagged and reviewed" is not a state
    the workflow can reach, and a pair of booleans would let it be written.
    Remembering that a reviewed item had once been flagged would only be worth
    the field if what flagged it were recorded too, and nothing needs that yet.

    Only items whose schema is a review unit carry a meaningful value; the rest
    stay ``NOT_REVIEWED`` and are reviewed through the unit that contains them.
    """

    NOT_REVIEWED = "not_reviewed"
    """Nobody has looked at it and nothing has asked them to."""
    FLAGGED = "flagged"
    """Something asked for review: a user, the import, or an invalid descendant
    found at import. Whatever raised it, only a user clears it — by reviewing."""
    REVIEWED = "reviewed"
    """Looked at and accepted. An item may be flagged again afterwards, which
    is how a later import reopens one."""
