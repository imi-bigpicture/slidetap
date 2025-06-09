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

from typing import Optional
from uuid import UUID

from slidetap.model.base_model import FrozenBaseModel


class ItemRelation(FrozenBaseModel):
    """Base class for all item relations."""

    uid: UUID
    name: str
    description: Optional[str] = None


class SampleToSampleRelation(ItemRelation):
    """Relation between two samples (parent-child relationship)."""

    parent_title: str
    child_title: str
    parent_uid: UUID
    child_uid: UUID
    min_parents: Optional[int] = None
    max_parents: Optional[int] = None
    min_children: Optional[int] = None
    max_children: Optional[int] = None


class ImageToSampleRelation(ItemRelation):
    """Relation between an image and a sample."""

    image_title: str
    sample_title: str
    image_uid: UUID
    sample_uid: UUID


class AnnotationToImageRelation(ItemRelation):
    """Relation between an annotation and an image."""

    annotation_title: str
    image_title: str
    annotation_uid: UUID
    image_uid: UUID


class ObservationRelation(ItemRelation):
    """Base class for observation relations."""

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
