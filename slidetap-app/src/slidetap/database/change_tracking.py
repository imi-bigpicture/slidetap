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

"""When what an item holds, or anything under it, last changed.

Kept on every flush rather than by the services that change items: an item is
changed through its own save, its attributes, its selection, a remap, or by
something being added or removed under it, and a time each of those paths had
to remember to write would be missing from the one that forgot.
"""

from collections.abc import Iterable
from datetime import datetime
from typing import Any

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from slidetap.database.attribute import DatabaseAttribute
from slidetap.database.item import (
    DatabaseAnnotation,
    DatabaseImage,
    DatabaseItem,
    DatabaseObservation,
    DatabaseSample,
)

_NOT_CHANGES_TO_ITEMS = frozenset(
    {
        # Bookkeeping about the item, rather than what it holds: locking and
        # unlocking a batch, validating it again, or flagging it for review
        # leave what was verified as it was.
        "locked",
        "review_status",
        "last_saved",
        "last_changed",
        "valid_attributes",
        "valid_relations",
        "valid_pseudonym",
        "review_issues",
        "review_issues_answered_on",
        "verification_entries",
        # Where an image is in being fetched, processed and stored. Moving it
        # to the outbox when the project is completed, or processing it for
        # another batch it is shared with, leaves its case as it was verified.
        "status",
        "status_message",
        "folder_path",
        "thumbnail_path",
        "metadata_digest",
        "format",
        "files",
    }
)
"""What an item can have changed without what it holds having changed."""

_NOT_CHANGES_TO_ATTRIBUTES = frozenset({"locked", "valid", "read_only"})
"""The same, for an attribute."""


def direct_parents(item: DatabaseItem) -> Iterable[DatabaseItem]:
    """What ``item`` hangs directly under."""
    if isinstance(item, DatabaseSample):
        return item.parents
    if isinstance(item, DatabaseImage):
        return item.samples
    if isinstance(item, DatabaseAnnotation):
        return [item.image] if item.image is not None else []
    if isinstance(item, DatabaseObservation):
        return [
            related
            for related in (item.sample, item.image, item.annotation)
            if related is not None
        ]
    return []


def _has_changed(entity: Any, ignored: frozenset[str]) -> bool:
    """Whether anything but what is ``ignored`` has changed on ``entity``.

    Only what was touched since it was loaded is looked at: a flush that locks
    a batch touches every item and attribute in it, and looking through every
    attribute of each for what changed would cost that flush most of its time.
    """
    state = inspect(entity)
    touched = set(state.attrs.keys()) - state.unmodified - ignored
    return any(state.attrs[key].history.has_changes() for key in touched)


@event.listens_for(Session, "before_flush")
def _stamp_changed_items(session: Session, *_: Any) -> None:
    """Stamp the items changed in the flush, and everything above them.

    Above as well as the item itself: a case is what is verified, and it has
    changed when a block under it has. Removed items stamp only what they hung
    under, which is what changed by losing them.
    """
    changed: list[DatabaseItem] = []
    removed: list[DatabaseItem] = []
    owner_uids: set[Any] = set()
    # Taken once: each is a new set of everything in the session each time it
    # is asked for, which asked per entity is quadratic in a large flush.
    new, deleted = session.new, session.deleted
    for entity in (*new, *session.dirty, *deleted):
        if isinstance(entity, DatabaseItem):
            if entity in deleted:
                removed.append(entity)
            elif entity in new or _has_changed(entity, _NOT_CHANGES_TO_ITEMS):
                changed.append(entity)
        elif isinstance(entity, DatabaseAttribute) and (
            entity in new
            or entity in deleted
            or _has_changed(entity, _NOT_CHANGES_TO_ATTRIBUTES)
        ):
            owner_uids.update(
                uid
                for uid in (
                    entity.attribute_item_uid,
                    entity.private_attribute_item_uid,
                )
                if uid is not None
            )
    if not changed and not removed and not owner_uids:
        return
    now = datetime.now()
    stamped: set[Any] = set()
    with session.no_autoflush:
        for owner_uid in owner_uids:
            owner = session.get(DatabaseItem, owner_uid)
            if owner is not None:
                changed.append(owner)
        for item in changed:
            stamp_with_ancestors(item, now, stamped)
        for item in removed:
            for parent in direct_parents(item):
                stamp_with_ancestors(parent, now, stamped)


def stamp_with_ancestors(item: DatabaseItem, now: datetime, stamped: set[Any]) -> None:
    """Stamp ``item`` and everything it hangs under, each once per flush."""
    level = [item]
    while level:
        above: list[DatabaseItem] = []
        for current in level:
            if current.uid is not None and current.uid in stamped:
                continue
            if current.uid is not None:
                stamped.add(current.uid)
            current.last_changed = now
            above.extend(direct_parents(current))
        level = above
