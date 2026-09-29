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

import logging
from collections.abc import Iterable
from typing import NamedTuple
from uuid import UUID

from sqlalchemy.orm import Session

from slidetap.database import (
    DatabaseAnnotation,
    DatabaseImage,
    DatabaseItem,
    DatabaseObservation,
    DatabaseSample,
)
from slidetap.model.schema.item_relation import (
    AnnotationToImageRelation,
    ObservationRelation,
)
from slidetap.services.database_service import DatabaseService
from slidetap.services.schema_service import SchemaService


class RelationResult(NamedTuple):
    """Whether one of an item's relations is satisfied, and which one it is.

    Named rather than a pair, so that what is being read stays legible where
    the results are counted and where the unsatisfied ones are listed.
    """

    name: str
    """The relation, as the schema names it."""

    satisfied: bool
    """Whether the item holds what the relation asks of it."""

    related: tuple[DatabaseItem, ...] = ()
    """What the item holds on the other side of the relation, in the project
    or not. What was counted is the selected ones among these; the rest is
    what selecting the item would have to bring in to satisfy it."""


class RelationValidator:
    def __init__(
        self, schema_service: SchemaService, database_service: DatabaseService
    ):
        self._schema_service = schema_service
        self._database_service = database_service
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def validate_item_relations(
        self,
        item: DatabaseItem,
        session: Session,
        visited: set[UUID] | None = None,
    ) -> bool:
        """Recompute and store ``valid_relations`` for an item and the other
        side of each relation it holds.

        Parameters
        ----------
        visited: set[UUID] | None
            Items already validated in this pass, added to as it goes. Given
            one, an item is validated at most once however many of its
            relations lead back to it, which is what keeps validating a whole
            import result linear rather than quadratic in its items.

            Only safe once the items involved are in their final state: an
            item validated before the rest of its relations are stored would
            be skipped, and keep the answer it had at the time. Left as
            ``None``, every visit revalidates, which is what a single item
            changing on its own needs.
        """
        if isinstance(item, DatabaseAnnotation):
            return self._validate_annotation_relations(session, item, visited=visited)
        if isinstance(item, DatabaseObservation):
            return self._validate_observation_relations(session, item, visited=visited)
        if isinstance(item, DatabaseImage):
            return self._validate_image_relations(session, item, visited=visited)
        if isinstance(item, DatabaseSample):
            return self._validate_sample_relations(session, item, visited=visited)
        raise ValueError(f"Item {item} is not a valid item type.")

    @staticmethod
    def _already_visited(item: DatabaseItem, visited: set[UUID] | None) -> bool:
        """Whether this pass has validated the item already, marking it as
        validated if not."""
        if visited is None:
            return False
        if item.uid in visited:
            return True
        visited.add(item.uid)
        return False

    def _validate_annotation_relations(
        self,
        session: Session,
        annotation: DatabaseAnnotation,
        other_side: bool = True,
        visited: set[UUID] | None = None,
    ) -> bool:
        if self._already_visited(annotation, visited):
            return bool(annotation.valid_relations)
        annotation.valid_relations = all(
            result.satisfied
            for result in self._annotation_relation_results(
                session, annotation, other_side=other_side, visited=visited
            )
        )
        self._logger.debug(
            f"Relations for annotation {annotation.uid}: "
            f"{'valid' if annotation.valid_relations else 'invalid'}."
        )
        return annotation.valid_relations

    def _annotation_relation_results(
        self,
        session: Session,
        annotation: DatabaseAnnotation,
        non_complete_relations: frozenset[UUID] = frozenset(),
        other_side: bool = True,
        visited: set[UUID] | None = None,
    ) -> list[RelationResult]:
        schema = self._schema_service.annotations[annotation.schema_uid]
        image = annotation.image
        image_relation = self._annotation_image_relation(schema.images, image)
        # The image is structural: an annotation is on exactly one, so the only
        # question is whether that one is still in the project.
        results = [
            RelationResult(
                image_relation.name if image_relation is not None else "Image",
                image is not None and image.selected,
                () if image is None else (image,),
            )
        ]
        if other_side and image is not None and image.selected:
            self._logger.debug(
                f"Validation relations for image {image.uid} "
                f"as other side of annotation {annotation.uid}."
            )
            self._validate_image_relations(
                session, image, other_side=False, visited=visited
            )
        results.extend(
            self._observation_relation_results(
                session,
                annotation,
                schema.observations,
                non_complete_relations=non_complete_relations,
                other_side=other_side,
                visited=visited,
            )
        )
        return results

    @staticmethod
    def _annotation_image_relation(
        relations: Iterable[AnnotationToImageRelation], image: DatabaseImage | None
    ) -> AnnotationToImageRelation | None:
        """The relation an annotation's image is held under, or ``None`` for an
        annotation on no image."""
        if image is None:
            return None
        try:
            return next(
                relation
                for relation in relations
                if relation.image_uid == image.schema_uid
            )
        except StopIteration as exception:
            schema_image_uids = [relation.image_uid for relation in relations]
            raise ValueError(
                f"Annotation is on an image with schema {image.schema_uid} that "
                f"is not in the annotation schema: {schema_image_uids}."
            ) from exception

    def _observation_relation_results(
        self,
        session: Session,
        subject: DatabaseSample | DatabaseImage | DatabaseAnnotation,
        relations: Iterable[ObservationRelation],
        non_complete_relations: frozenset[UUID] = frozenset(),
        other_side: bool = True,
        visited: set[UUID] | None = None,
    ) -> list[RelationResult]:
        """Whether a subject holds the observations each of its observation
        relations asks of it. Counted per relation, since a subject may need
        one kind of observation and merely allow another."""
        results: list[RelationResult] = []
        for relation in relations:
            if relation.uid in non_complete_relations:
                continue
            observations_of_type = [
                observation
                for observation in subject.observations
                if observation.schema_uid == relation.observation_uid
            ]
            selected_count = len(
                [
                    observation
                    for observation in observations_of_type
                    if observation.selected
                ]
            )
            results.append(
                RelationResult(
                    relation.name,
                    relation.observations.allows(selected_count),
                    tuple(observations_of_type),
                )
            )
            if other_side:
                self._logger.debug(
                    f"Validation relations for observations "
                    f"{[observation.uid for observation in observations_of_type]} "
                    f"as other side of {subject.uid}."
                )
                for observation in observations_of_type:
                    self._validate_observation_relations(
                        session, observation, other_side=False, visited=visited
                    )
        return results

    def _validate_observation_relations(
        self,
        session: Session,
        observation: DatabaseObservation,
        other_side: bool = True,
        visited: set[UUID] | None = None,
    ) -> bool:
        if self._already_visited(observation, visited):
            return bool(observation.valid_relations)
        observation.valid_relations = all(
            result.satisfied
            for result in self._observation_subject_results(
                session, observation, other_side=other_side, visited=visited
            )
        )
        self._logger.debug(
            f"Relations for observation {observation.uid}: "
            f"{'valid' if observation.valid_relations else 'invalid'}."
        )
        return observation.valid_relations

    def _observation_subject_results(
        self,
        session: Session,
        observation: DatabaseObservation,
        other_side: bool = True,
        visited: set[UUID] | None = None,
    ) -> list[RelationResult]:
        """The one relation an observation has: to the thing it is on, which
        has to be in the project for the observation to be. Which of the
        schema's relations that is depends on what the thing is."""
        schema = self._schema_service.observations[observation.schema_uid]
        subject: DatabaseItem | None
        if observation.image is not None:
            subject = observation.image
            relation = self._subject_relation(
                ((relation, relation.image_uid) for relation in schema.images),
                observation,
                subject,
                "image",
            )
        elif observation.sample is not None:
            subject = observation.sample
            relation = self._subject_relation(
                ((relation, relation.sample_uid) for relation in schema.samples),
                observation,
                subject,
                "sample",
            )
        elif observation.annotation is not None:
            subject = observation.annotation
            relation = self._subject_relation(
                (
                    (relation, relation.annotation_uid)
                    for relation in schema.annotations
                ),
                observation,
                subject,
                "annotation",
            )
        else:
            subject = None
            relation = None
        satisfied = subject is not None and subject.selected
        if other_side and satisfied:
            self._logger.debug(
                f"Validation relations for {subject.uid} as other side of "
                f"observation {observation.uid}."
            )
            self._validate_subject_relations(session, subject, visited)
        return [
            RelationResult(
                relation.name if relation is not None else "Subject",
                satisfied,
                () if subject is None else (subject,),
            )
        ]

    @staticmethod
    def _subject_relation(
        relations: Iterable[tuple[ObservationRelation, UUID]],
        observation: DatabaseObservation,
        subject: DatabaseItem,
        kind: str,
    ) -> ObservationRelation:
        """The relation the observation's subject is held under, among those
        given with the schema uid each one is to."""
        candidates = list(relations)
        try:
            return next(
                relation
                for relation, subject_schema_uid in candidates
                if subject_schema_uid == subject.schema_uid
            )
        except StopIteration as exception:
            schema_uids = [subject_schema_uid for _, subject_schema_uid in candidates]
            raise ValueError(
                f"Observation {observation.uid} is on {kind} with schema "
                f"{subject.schema_uid} that is not in the observation schema: "
                f"{schema_uids}."
            ) from exception

    def _validate_subject_relations(
        self, session: Session, subject: DatabaseItem, visited: set[UUID] | None
    ) -> None:
        if isinstance(subject, DatabaseImage):
            self._validate_image_relations(
                session, subject, other_side=False, visited=visited
            )
        elif isinstance(subject, DatabaseSample):
            self._validate_sample_relations(
                session, subject, other_side=False, visited=visited
            )
        elif isinstance(subject, DatabaseAnnotation):
            self._validate_annotation_relations(
                session, subject, other_side=False, visited=visited
            )

    def relations_are_valid(
        self,
        item: DatabaseItem,
        session: Session,
        non_complete_relations: frozenset[UUID] = frozenset(),
    ) -> bool:
        """Whether an item's relations are valid, leaving ``valid_relations``
        as it stands.

        Parameters
        ----------
        item: DatabaseItem
            The item to count the relations of.
        session: Session
            Session to read the related items in.
        non_complete_relations: frozenset[UUID]
            Relations not to count, by relation uid. Empty answers with the
            stored ``valid_relations`` and reads nothing.

        Returns
        -------
        bool
            Whether the relations counted are satisfied. Not stored on the
            item: leaving relations out answers a narrower question than
            ``valid_relations``, which counts every relation and is what the
            rest of the application reads.
        """
        if not non_complete_relations:
            return bool(item.valid_relations)
        return all(
            result.satisfied
            for result in self.relation_results(
                item, session, non_complete_relations=non_complete_relations
            )
        )

    def not_satisfied_relations(
        self, item: DatabaseItem, session: Session
    ) -> list[str]:
        """The relations an item does not satisfy, by the name the schema gives
        them, so that what is wrong can be said rather than counted."""
        return [
            result.name
            for result in self.relation_results(item, session)
            if not result.satisfied
        ]

    def relation_results(
        self,
        item: DatabaseItem,
        session: Session,
        non_complete_relations: frozenset[UUID] = frozenset(),
    ) -> list[RelationResult]:
        """Whether each of an item's relations is satisfied, by name and with
        what is on the other side of it. Counted for the item alone as it
        stands in the session, committed or not, leaving what is stored on the
        other side of each relation as it is."""
        if isinstance(item, DatabaseObservation):
            return self._observation_subject_results(session, item, other_side=False)
        if isinstance(item, DatabaseSample):
            return self._sample_relation_results(
                session,
                item,
                non_complete_relations=non_complete_relations,
                other_side=False,
            )
        if isinstance(item, DatabaseImage):
            return self._image_relation_results(
                session,
                item,
                non_complete_relations=non_complete_relations,
                other_side=False,
            )
        if isinstance(item, DatabaseAnnotation):
            return self._annotation_relation_results(
                session,
                item,
                non_complete_relations=non_complete_relations,
                other_side=False,
            )
        return []

    def _validate_image_relations(
        self,
        session: Session,
        image: DatabaseImage,
        other_side: bool = True,
        visited: set[UUID] | None = None,
    ) -> bool:
        if self._already_visited(image, visited):
            return bool(image.valid_relations)
        image.valid_relations = all(
            result.satisfied
            for result in self._image_relation_results(
                session, image, other_side=other_side, visited=visited
            )
        )
        self._logger.debug(
            f"Relations for image {image.uid}: "
            f"{'valid' if image.valid_relations else 'invalid'}."
        )
        return image.valid_relations

    def _image_relation_results(
        self,
        session: Session,
        image: DatabaseImage,
        non_complete_relations: frozenset[UUID] = frozenset(),
        other_side: bool = True,
        visited: set[UUID] | None = None,
    ) -> list[RelationResult]:
        schema = self._schema_service.images[image.schema_uid]
        selected_samples = [
            sample for sample in (image.samples or []) if sample.selected
        ]
        # Counted per relation rather than in one heap: an image may be allowed
        # several samples of one schema and only one of another, and a sample of
        # a schema the image schema does not relate to satisfies nothing.
        # Orphan relations are skipped, so an image parked on one has nothing
        # counted towards the samples it is required to have, and is invalid
        # until it is moved to the sample it is actually of.
        results: list[RelationResult] = []
        for relation in schema.samples:
            if relation.orphan or relation.uid in non_complete_relations:
                continue
            samples_of_type = [
                sample
                for sample in (image.samples or [])
                if sample.schema_uid == relation.sample_uid
            ]
            selected_count = len(
                [sample for sample in samples_of_type if sample.selected]
            )
            results.append(
                RelationResult(
                    relation.name,
                    relation.samples.allows(selected_count),
                    tuple(samples_of_type),
                )
            )
        if other_side:
            self._logger.debug(
                f"Validation relations for samples "
                f"{[sample.uid for sample in selected_samples]} "
                f"as other side of image {image.uid}."
            )
            for sample in selected_samples:
                self._validate_sample_relations(
                    session, sample, other_side=False, visited=visited
                )
        for relation in schema.annotations:
            if relation.uid in non_complete_relations:
                continue
            annotations_of_type = [
                annotation
                for annotation in image.annotations
                if annotation.schema_uid == relation.annotation_uid
            ]
            selected_count = len(
                [
                    annotation
                    for annotation in annotations_of_type
                    if annotation.selected
                ]
            )
            results.append(
                RelationResult(
                    relation.name,
                    relation.annotations.allows(selected_count),
                    tuple(annotations_of_type),
                )
            )
            if other_side:
                for annotation in annotations_of_type:
                    self._validate_annotation_relations(
                        session, annotation, other_side=False, visited=visited
                    )
        results.extend(
            self._observation_relation_results(
                session,
                image,
                schema.observations,
                non_complete_relations=non_complete_relations,
                other_side=other_side,
                visited=visited,
            )
        )
        return results

    def _validate_sample_relations(
        self,
        session: Session,
        sample: DatabaseSample,
        other_side: bool = True,
        visited: set[UUID] | None = None,
    ) -> bool:
        if self._already_visited(sample, visited):
            return bool(sample.valid_relations)
        sample.valid_relations = all(
            result.satisfied
            for result in self._sample_relation_results(
                session, sample, other_side=other_side, visited=visited
            )
        )
        return sample.valid_relations

    def _sample_relation_results(
        self,
        session: Session,
        sample: DatabaseSample,
        non_complete_relations: frozenset[UUID] = frozenset(),
        other_side: bool = True,
        visited: set[UUID] | None = None,
    ) -> list[RelationResult]:
        schema = self._schema_service.samples[sample.schema_uid]
        results: list[RelationResult] = []
        for relation in schema.children:
            if relation.uid in non_complete_relations:
                continue
            children_of_type = self._database_service.get_sample_children(
                session, sample, relation.child_uid
            )
            selected_children_count = len(
                [child for child in children_of_type if child.selected]
            )
            self._logger.debug(
                f"Validating relation for sample {sample.uid} to children "
                f"{[child.uid for child in children_of_type]}."
            )
            results.append(
                RelationResult(
                    relation.name,
                    relation.children.allows(selected_children_count),
                    tuple(children_of_type),
                )
            )
            if other_side:
                self._logger.debug(
                    f"Validation relations for children "
                    f"{[child.uid for child in children_of_type]} "
                    f"as other side of sample {sample.uid}."
                )
                for child in children_of_type:
                    self._validate_sample_relations(
                        session, child, other_side=False, visited=visited
                    )

        for relation in schema.parents:
            if relation.uid in non_complete_relations:
                continue
            parents_of_type = self._database_service.get_sample_parents(
                session, sample, relation.parent_uid
            )
            selected_parent_count = len(
                [parent for parent in parents_of_type if parent.selected]
            )
            self._logger.debug(
                f"Validating relation for sample {sample.uid} to parents "
                f"{[parent.uid for parent in parents_of_type]}."
            )

            results.append(
                RelationResult(
                    relation.name,
                    relation.parents.allows(selected_parent_count),
                    tuple(parents_of_type),
                )
            )
            if other_side:
                self._logger.debug(
                    f"Validation relations for parents "
                    f"{[parent.uid for parent in parents_of_type]} "
                    f"as other side of sample {sample.uid}."
                )
                for parent in parents_of_type:
                    self._validate_sample_relations(
                        session, parent, other_side=False, visited=visited
                    )
        for relation in schema.images:
            # An orphan relation says nothing about this sample: it is where
            # images that belong elsewhere are parked, so holding one neither
            # satisfies a requirement nor breaks one.
            if relation.orphan or relation.uid in non_complete_relations:
                continue
            images_of_type = self._database_service.get_sample_images(
                session, sample, relation.image_uid
            )
            selected_images = len([image for image in images_of_type if image.selected])
            results.append(
                RelationResult(
                    relation.name,
                    relation.images.allows(selected_images),
                    tuple(images_of_type),
                )
            )
            if other_side:
                for image in images_of_type:
                    self._validate_image_relations(
                        session, image, other_side=False, visited=visited
                    )
        results.extend(
            self._observation_relation_results(
                session,
                sample,
                schema.observations,
                non_complete_relations=non_complete_relations,
                other_side=other_side,
                visited=visited,
            )
        )
        return results
