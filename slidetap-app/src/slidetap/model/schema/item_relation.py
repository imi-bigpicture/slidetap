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

"""Item relation models for defining relationships between different types of items."""

from enum import Enum
from uuid import UUID

from slidetap.model.base_model import FrozenBaseModel


class Cardinality(Enum):
    """How many items a relation allows on one side of itself.

    Named for the multiplicity rather than for its bounds, so a declaration
    states what it permits without a lookup. The four values are the whole
    space: a minimum of zero or one, and a maximum of one or unbounded.
    Nothing in this domain asks for "at most five", and spelling bounds as
    numbers gave every constraint two spellings — ``None`` and ``0`` both
    meaning unbounded below — which each validator then had to handle.

    Examples
    --------
    >>> Cardinality.ONE.allows(0), Cardinality.ONE.allows(1)
    (False, True)
    >>> Cardinality.ONE_OR_MORE.allows(3)
    True
    >>> Cardinality.ZERO_OR_ONE.allows(2)
    False
    """

    ONE = "one"
    """Exactly one — 1..1."""
    ZERO_OR_ONE = "zero_or_one"
    """At most one — 0..1."""
    ONE_OR_MORE = "one_or_more"
    """At least one — 1..*."""
    ZERO_OR_MORE = "zero_or_more"
    """Any number, none included — 0..*."""

    @property
    def required(self) -> bool:
        """At least one is needed."""
        return self in (Cardinality.ONE, Cardinality.ONE_OR_MORE)

    @property
    def multiple(self) -> bool:
        """More than one is permitted."""
        return self in (Cardinality.ONE_OR_MORE, Cardinality.ZERO_OR_MORE)

    def allows(self, count: int) -> bool:
        """Whether ``count`` items satisfy this cardinality."""
        if self.required and count < 1:
            return False
        return self.multiple or count <= 1


class ItemRelation(FrozenBaseModel):
    """Base class for all item relations."""

    uid: UUID
    name: str
    description: str | None = None


class SampleToSampleRelation(ItemRelation):
    """Relation between two samples (parent-child relationship)."""

    parent_title: str
    child_title: str
    parent_uid: UUID
    child_uid: UUID
    parents: Cardinality = Cardinality.ZERO_OR_MORE
    """How many parents of ``parent_uid`` a child may have."""
    children: Cardinality = Cardinality.ZERO_OR_MORE
    """How many children of ``child_uid`` a parent may have."""


class ImageToSampleRelation(ItemRelation):
    """Relation between an image and a sample."""

    image_title: str
    sample_title: str
    image_uid: UUID
    sample_uid: UUID
    images: Cardinality = Cardinality.ONE_OR_MORE
    """How many images a sample may have — a slide that has been scanned more
    than once has more than one."""
    samples: Cardinality = Cardinality.ONE_OR_MORE
    """How many samples an image may be of — more than one where an image
    covers several, as a macro image over a whole case does."""


class AnnotationToImageRelation(ItemRelation):
    """Relation between an annotation and an image."""

    annotation_title: str
    image_title: str
    annotation_uid: UUID
    image_uid: UUID


class ObservationRelation(ItemRelation):
    """Base class for observation relations.

    No cardinality: an observation holds a single subject reference and an
    annotation a single image, so one is structural rather than declared.
    A field here could not be set to anything else.
    """

    observation_title: str
    observation_uid: UUID


class ObservationToSampleRelation(ObservationRelation):
    """Relation between an observation and a sample."""

    sample_title: str
    sample_uid: UUID


class ObservationToImageRelation(ObservationRelation):
    """Relation between an observation and an image."""

    image_title: str
    image_uid: UUID


class ObservationToAnnotationRelation(ObservationRelation):
    """Relation between an observation and an annotation."""

    annotation_title: str
    annotation_uid: UUID
