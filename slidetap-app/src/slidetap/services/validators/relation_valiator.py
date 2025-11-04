import logging
from typing import List

from slidetap.database import (
    DatabaseAnnotation,
    DatabaseImage,
    DatabaseItem,
    DatabaseObservation,
    DatabaseSample,
)
from slidetap.services.database_service import DatabaseService
from slidetap.services.schema_service import SchemaService
from sqlalchemy.orm import Session


class RelationValidator:
    def __init__(
        self, schema_service: SchemaService, database_service: DatabaseService
    ):
        self._schema_service = schema_service
        self._database_service = database_service

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
            logging.debug(
                f"Valid relation for annotation {annotation.uid} to image {annotation.image.uid}."
            )
            annotation.valid_relations = True
            if other_side:
                logging.debug(
                    f"Validation relations for image {annotation.image.uid} as other side of annotation {annotation.uid}."
                )
                self._validate_image_relations(
                    session, annotation.image, other_side=False
                )
        else:
            logging.debug(f"No valid relation for annotation {annotation.uid}.")
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
        logging.debug(
            f"Validating relations for observation {observation.uid} of schema {observation.schema_uid} with name {schema.name}."
        )
        if observation.image is not None and observation.image.selected:
            logging.debug(
                f"Valid relation for observation {observation.uid} to image {observation.image.uid}."
            )
            try:
                relation = next(
                    relation
                    for relation in schema.images
                    if relation.image_uid == observation.image.schema_uid
                )
            except StopIteration:
                raise ValueError(
                    f"Observation {observation.uid} is on an image with schema {observation.image.schema_uid} that is not in the observation schema: {[image.image_uid for image in schema.images]}."
                )
            if other_side:
                logging.debug(
                    f"Validation relations for image {observation.image.uid} as other side of observation {observation.uid}."
                )
                self._validate_image_relations(
                    session, observation.image, other_side=False
                )
        elif observation.sample is not None and observation.sample.selected:
            logging.debug(
                f"Valid relation for observation {observation.uid} to sample {observation.sample.uid}."
            )
            try:
                relation = next(
                    relation
                    for relation in schema.samples
                    if relation.sample_uid == observation.sample.schema_uid
                )
            except StopIteration:
                raise ValueError(
                    f"Observation {observation.uid} is on a sample with schema {observation.sample.schema_uid} that is not in the observation schema: {[sample.sample_uid for sample in schema.samples]}."
                )
            if other_side:
                logging.debug(
                    f"Validation relations for sample {observation.sample.uid} as other side of observation {observation.uid}."
                )
                self._validate_sample_relations(
                    session, observation.sample, other_side=False
                )

        elif observation.annotation is not None and observation.annotation.selected:
            logging.debug(
                f"Valid relation for observation {observation.uid} to annotation {observation.annotation.uid}."
            )
            try:
                relation = next(
                    relation
                    for relation in schema.annotations
                    if relation.annotation_uid == observation.annotation.schema_uid
                )
            except StopIteration:
                raise ValueError(
                    f"Observation {observation.uid} is on an annotation with schema {observation.annotation.schema_uid} that is not in the observation schema: {[annotation.annotation_uid for annotation in schema.annotations]}."
                )
            if other_side:
                logging.debug(
                    f"Validation relations for annotation {observation.annotation.uid} as other side of observation {observation.uid}."
                )
                self._validate_annotation_relations(
                    session, observation.annotation, other_side=False
                )
        if relation is not None:
            observation.valid_relations = True
        else:
            logging.debug(f"No valid relation for observation {observation.uid}.")
            observation.valid_relations = False
        return observation.valid_relations

    def _validate_image_relations(
        self, session: Session, image: DatabaseImage, other_side: bool = True
    ) -> bool:
        if image.samples is not None and len(image.samples) > 0:
            logging.debug(
                f"Valid relation for image {image.uid} to samples {[sample.uid for sample in image.samples]}."
            )
            image.valid_relations = True
            if other_side:
                logging.debug(
                    f"Validation relations for samples {[sample.uid for sample in image.samples]} as other side of image {image.uid}."
                )
                for sample in image.samples:
                    self._validate_sample_relations(session, sample, other_side=False)
        else:
            logging.debug(f"No valid relation for image {image.uid} to samples.")
            image.valid_relations = False
        return image.valid_relations

    def _validate_sample_relations(
        self, session: Session, sample: DatabaseSample, other_side: bool = True
    ) -> bool:
        schema = self._schema_service.samples[sample.schema_uid]
        results: List[bool] = []
        for relation in schema.children:
            children_of_type = self._database_service.get_sample_children(
                session, sample, relation.child_uid
            )
            selected_children_count = len(
                [child for child in children_of_type if child.selected]
            )
            logging.debug(
                f"Validating relation for sample {sample.uid} to children {[child.uid for child in children_of_type]}."
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
                logging.debug(
                    f"Validation relations for children {[child.uid for child in children_of_type]} as other side of sample {sample.uid}."
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
            logging.debug(
                f"Validating relation for sample {sample.uid} to parents {[parent.uid for parent in parents_of_type]}."
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
                logging.debug(
                    f"Validation relations for parents {[parent.uid for parent in parents_of_type]} as other side of sample {sample.uid}."
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
