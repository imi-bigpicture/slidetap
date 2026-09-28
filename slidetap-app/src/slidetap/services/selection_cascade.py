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

"""What follows an item into or out of the project.

Selected means the item goes into the bundle. Taking an item out or putting it
back is therefore never about that item alone: an image of a slide that is
out has no place to go, and a slide put back has nowhere to go without its
block. What follows is read off the schema rather than written per item type.
Every relation declares how many of the other side an item may hold, and the
same count that decides whether an item is valid decides what has to move
with it:

- Deselecting an item deselects each related item that a relation of its no
  longer allows once the item is out, and so on outward. A block whose last
  slide goes is deselected if the schema says a block needs a slide; a macro
  image over two blocks stays when one of them goes, since the other still
  satisfies it.
- Selecting an item selects, for each relation the item requires at least one
  of and now holds none, everything it has on that relation, and so on
  outward. A slide put back brings its block, and the block its specimen, as
  far up as the schema requires.

One thing is not left to the cardinalities. An item that hangs under others,
an image under its samples or a child sample under its parents, is deselected
when the last of what it hung under goes, whatever the relation allows. What
the relation allows describes the data; an image whose every slide is out of
the project is not data anyone asked for. Selecting such an item likewise
brings back what it hangs under when none of it is in.

What the cascade does not do is keep the project valid. A selection that
leaves an item short of what its schema asks is allowed, and the item is
marked as not valid until a curator settles it, since a batch does not
complete while anything in it is not valid.
"""

import logging
from collections import deque
from collections.abc import Iterable

from sqlalchemy.orm import Session

from slidetap.database import (
    DatabaseAnnotation,
    DatabaseImage,
    DatabaseItem,
    DatabaseObservation,
    DatabaseSample,
)
from slidetap.services.validation_service import ValidationService


class SelectionCascade:
    def __init__(self, validation_service: ValidationService):
        self._validation_service = validation_service
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def deselect(self, item: DatabaseItem, session: Session) -> list[DatabaseItem]:
        """Take an item out of the project with everything that cannot stay
        without it. Returns what was deselected, the item first, in the order
        it happened. Nothing is committed."""
        deselected: list[DatabaseItem] = []
        queue: deque[DatabaseItem] = deque([item])
        while queue:
            current = queue.popleft()
            if not current.selected:
                continue
            neighbours = [
                neighbour
                for neighbour in self._neighbours(current)
                if neighbour.selected
            ]
            before = {
                neighbour.uid: self._satisfied(neighbour, session)
                for neighbour in neighbours
            }
            current.selected = False
            deselected.append(current)
            for neighbour in neighbours:
                if self._newly_unsatisfied(
                    before[neighbour.uid], self._satisfied(neighbour, session)
                ) or self._hangs_under_nothing_selected(neighbour):
                    queue.append(neighbour)
        self._logger.debug(
            f"Deselecting {item.uid} deselected "
            f"{[deselected_item.uid for deselected_item in deselected]}."
        )
        return deselected

    def select(self, item: DatabaseItem, session: Session) -> list[DatabaseItem]:
        """Put an item into the project with everything it cannot be in
        without. Returns what was selected, the item first, in the order it
        happened. Nothing is committed."""
        selected: list[DatabaseItem] = []
        queue: deque[DatabaseItem] = deque([item])
        while queue:
            current = queue.popleft()
            if current.selected:
                continue
            current.selected = True
            selected.append(current)
            for result in self._validation_service.relation_results(current, session):
                # Unsatisfied with something selected on it is too many, which
                # nothing can be selected to mend. Unsatisfied with nothing
                # selected is too few, and everything held on the relation is
                # what mends it.
                if result.satisfied or any(
                    related.selected for related in result.related
                ):
                    continue
                queue.extend(result.related)
            if self._hangs_under_nothing_selected(current):
                queue.extend(self._hangs_under(current))
        self._logger.debug(
            f"Selecting {item.uid} selected "
            f"{[selected_item.uid for selected_item in selected]}."
        )
        return selected

    def _satisfied(self, item: DatabaseItem, session: Session) -> list[bool]:
        """Whether each relation of the item is satisfied, in the order the
        validator lists them, which is the same each time for one schema."""
        return [
            result.satisfied
            for result in self._validation_service.relation_results(item, session)
        ]

    @staticmethod
    def _newly_unsatisfied(before: list[bool], after: list[bool]) -> bool:
        return any(
            was_satisfied and not is_satisfied
            for was_satisfied, is_satisfied in zip(before, after, strict=True)
        )

    @staticmethod
    def _neighbours(item: DatabaseItem) -> Iterable[DatabaseItem]:
        """Everything the item is directly related to, on either side."""
        if isinstance(item, DatabaseSample):
            yield from item.parents
            yield from item.children
            yield from item.images
            yield from item.observations
        elif isinstance(item, DatabaseImage):
            yield from item.samples
            yield from item.annotations
            yield from item.observations
        elif isinstance(item, DatabaseAnnotation):
            if item.image is not None:
                yield item.image
            yield from item.observations
        elif isinstance(item, DatabaseObservation):
            for subject in (item.image, item.sample, item.annotation):
                if subject is not None:
                    yield subject

    @staticmethod
    def _hangs_under(item: DatabaseItem) -> list[DatabaseItem]:
        """What the item is attached beneath. Empty for one at the top of its
        hierarchy, or for an observation or annotation, whose single subject
        is a relation the validator already counts."""
        if isinstance(item, DatabaseSample):
            return list(item.parents)
        if isinstance(item, DatabaseImage):
            return list(item.samples)
        return []

    def _hangs_under_nothing_selected(self, item: DatabaseItem) -> bool:
        holders = self._hangs_under(item)
        return bool(holders) and not any(holder.selected for holder in holders)
