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
from uuid import UUID

from typing import NamedTuple

from sqlalchemy.orm import Session

from slidetap.database import (
    DatabaseAnnotation,
    DatabaseImage,
    DatabaseItem,
    DatabaseObservation,
    DatabaseSample,
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
        if annotation.image is not None and annotation.image.selected:
            self._logger.debug(
                f"Valid relation for annotation {annotation.uid} "
                f"to image {annotation.image.uid}."
            )
            annotation.valid_relations = True
            if other_side:
                self._logger.debug(
                    f"Validation relations for image {annotation.image.uid} "
                    f"as other side of annotation {annotation.uid}."
                )
                self._validate_image_relations(
                    session, annotation.image, other_side=False, visited=visited
                )
        else:
            self._logger.debug(f"No valid relation for annotation {annotation.uid}.")
            annotation.valid_relations = False
        return annotation.valid_relations

    def _validate_observation_relations(
        self,
        session: Session,
        observation: DatabaseObservation,
        other_side: bool = True,
        visited: set[UUID] | None = None,
    ) -> bool:
        if self._already_visited(observation, visited):
            return bool(observation.valid_relations)
        relation = None
        schema = self._schema_service.observations[observation.schema_uid]
        self._logger.debug(
            f"Validating relations for observation {observation.uid} "
            f"of schema {observation.schema_uid} with name {schema.name}."
        )
        if observation.image is not None and observation.image.selected:
            self._logger.debug(
                f"Valid relation for observation {observation.uid} "
                f"to image {observation.image.uid}."
            )
            try:
                relation = next(
                    relation
                    for relation in schema.images
                    if relation.image_uid == observation.image.schema_uid
                )
            except StopIteration as exception:
                schema_image_uids = [image.image_uid for image in schema.images]
                raise ValueError(
                    f"Observation {observation.uid} is on an image with schema "
                    f"{observation.image.schema_uid} that is not in the "
                    f"observation schema: {schema_image_uids}."
                ) from exception
            if other_side:
                self._logger.debug(
                    f"Validation relations for image {observation.image.uid} "
                    f"as other side of observation {observation.uid}."
                )
                self._validate_image_relations(
                    session, observation.image, other_side=False, visited=visited
                )
        elif observation.sample is not None and observation.sample.selected:
            self._logger.debug(
                f"Valid relation for observation {observation.uid} "
                f"to sample {observation.sample.uid}."
            )
            try:
                relation = next(
                    relation
                    for relation in schema.samples
                    if relation.sample_uid == observation.sample.schema_uid
                )
            except StopIteration as exception:
                schema_sample_uids = [sample.sample_uid for sample in schema.samples]
                raise ValueError(
                    f"Observation {observation.uid} is on a sample with schema "
                    f"{observation.sample.schema_uid} that is not in the "
                    f"observation schema: {schema_sample_uids}."
                ) from exception
            if other_side:
                self._logger.debug(
                    f"Validation relations for sample {observation.sample.uid} "
                    f"as other side of observation {observation.uid}."
                )
                self._validate_sample_relations(
                    session, observation.sample, other_side=False, visited=visited
                )

        elif observation.annotation is not None and observation.annotation.selected:
            self._logger.debug(
                f"Valid relation for observation {observation.uid} "
                f"to annotation {observation.annotation.uid}."
            )
            try:
                relation = next(
                    relation
                    for relation in schema.annotations
                    if relation.annotation_uid == observation.annotation.schema_uid
                )
            except StopIteration as exception:
                schema_annotation_uids = [
                    annotation.annotation_uid for annotation in schema.annotations
                ]
                raise ValueError(
                    f"Observation {observation.uid} is on an annotation with "
                    f"schema {observation.annotation.schema_uid} that is not in "
                    f"the observation schema: {schema_annotation_uids}."
                ) from exception
            if other_side:
                self._logger.debug(
                    f"Validation relations for annotation "
                    f"{observation.annotation.uid} as other side of observation "
                    f"{observation.uid}."
                )
                self._validate_annotation_relations(
                    session, observation.annotation, other_side=False, visited=visited
                )
        if relation is not None:
            observation.valid_relations = True
        else:
            self._logger.debug(f"No valid relation for observation {observation.uid}.")
            observation.valid_relations = False
        return observation.valid_relations

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
            The item to count the relations of. Samples and images count theirs
            one by one and so have something to leave out; an observation or an
            annotation is on a single thing, and answers with what is stored.
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
            for result in self._relation_results(
                item, session, non_complete_relations=non_complete_relations
            )
        )

    def not_satisfied_relations(
        self, item: DatabaseItem, session: Session
    ) -> list[str]:
        """The relations an item does not satisfy, by the name the schema gives
        them, so that what is wrong can be said rather than counted.

        Empty for an observation or an annotation: each is on a single thing,
        and there is no relation of theirs to name apart from that one.
        """
        return [
            result.name
            for result in self._relation_results(item, session)
            if not result.satisfied
        ]

    def _relation_results(
        self,
        item: DatabaseItem,
        session: Session,
        non_complete_relations: frozenset[UUID] = frozenset(),
    ) -> list[RelationResult]:
        """Whether each of an item's relations is satisfied, by name. Counted
        for the item alone, leaving what is stored on the other side of each
        relation as it is."""
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
        results = [
            RelationResult(
                relation.name,
                relation.samples.allows(
                    len(
                        [
                            sample
                            for sample in selected_samples
                            if sample.schema_uid == relation.sample_uid
                        ]
                    )
                ),
            )
            for relation in schema.samples
            if not relation.orphan and relation.uid not in non_complete_relations
        ]
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
                    relation.name, relation.children.allows(selected_children_count)
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
                    relation.name, relation.parents.allows(selected_parent_count)
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
                RelationResult(relation.name, relation.images.allows(selected_images))
            )
            if other_side:
                for image in images_of_type:
                    self._validate_image_relations(
                        session, image, other_side=False, visited=visited
                    )
        return results
