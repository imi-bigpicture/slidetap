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


class RelationValidator:
    def __init__(
        self, schema_service: SchemaService, database_service: DatabaseService
    ):
        self._schema_service = schema_service
        self._database_service = database_service
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def validate_item_relations(self, item: DatabaseItem, session: Session) -> bool:
        if isinstance(item, DatabaseAnnotation):
            return self._validate_annotation_relations(session, item)
        if isinstance(item, DatabaseObservation):
            return self._validate_observation_relations(session, item)
        if isinstance(item, DatabaseImage):
            return self._validate_image_relations(session, item)
        if isinstance(item, DatabaseSample):
            return self._validate_sample_relations(session, item)
        raise ValueError(f"Item {item} is not a valid item type.")

    def _validate_annotation_relations(
        self, session: Session, annotation: DatabaseAnnotation, other_side: bool = True
    ) -> bool:
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
                    session, annotation.image, other_side=False
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
    ) -> bool:
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
                    session, observation.image, other_side=False
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
                    session, observation.sample, other_side=False
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
                    session, observation.annotation, other_side=False
                )
        if relation is not None:
            observation.valid_relations = True
        else:
            self._logger.debug(f"No valid relation for observation {observation.uid}.")
            observation.valid_relations = False
        return observation.valid_relations

    def _validate_image_relations(
        self, session: Session, image: DatabaseImage, other_side: bool = True
    ) -> bool:
        selected_samples = [
            sample for sample in (image.samples or []) if sample.selected
        ]
        if selected_samples:
            self._logger.debug(
                f"Valid relation for image {image.uid} to samples "
                f"{[sample.uid for sample in selected_samples]}."
            )
            image.valid_relations = True
            if other_side:
                self._logger.debug(
                    f"Validation relations for samples "
                    f"{[sample.uid for sample in selected_samples]} "
                    f"as other side of image {image.uid}."
                )
                for sample in selected_samples:
                    self._validate_sample_relations(session, sample, other_side=False)
        else:
            self._logger.debug(f"No valid relation for image {image.uid} to samples.")
            image.valid_relations = False
        return image.valid_relations

    def _validate_sample_relations(
        self, session: Session, sample: DatabaseSample, other_side: bool = True
    ) -> bool:
        schema = self._schema_service.samples[sample.schema_uid]
        results: list[bool] = []
        for relation in schema.children:
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
            valid = (
                relation.min_children is None
                or selected_children_count >= relation.min_children
            ) and (
                relation.max_children is None
                or selected_children_count <= relation.max_children
            )
            results.append(valid)
            if other_side:
                self._logger.debug(
                    f"Validation relations for children "
                    f"{[child.uid for child in children_of_type]} "
                    f"as other side of sample {sample.uid}."
                )
                for child in children_of_type:
                    self._validate_sample_relations(session, child, other_side=False)

        for relation in schema.parents:
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

            valid = (
                relation.min_parents is None
                or selected_parent_count >= relation.min_parents
            ) and (
                relation.max_parents is None
                or selected_parent_count <= relation.max_parents
            )
            results.append(valid)
            if other_side:
                self._logger.debug(
                    f"Validation relations for parents "
                    f"{[parent.uid for parent in parents_of_type]} "
                    f"as other side of sample {sample.uid}."
                )
                for parent in parents_of_type:
                    self._validate_sample_relations(session, parent, other_side=False)
        for relation in schema.images:
            images_of_type = self._database_service.get_sample_images(
                session, sample, relation.image_uid
            )
            selected_images = len([image for image in images_of_type if image.selected])
            valid = selected_images > 0
            results.append(valid)
            if other_side:
                for image in images_of_type:
                    self._validate_image_relations(session, image, other_side=False)
        sample.valid_relations = all(results)
        return sample.valid_relations
