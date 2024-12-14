from typing import Dict, Iterable, List, Optional, Union
from uuid import UUID

from flask import current_app

from slidetap.database import (
    DatabaseAnnotation,
    DatabaseAttribute,
    DatabaseImage,
    DatabaseItem,
    DatabaseObservation,
    DatabaseProject,
    DatabaseSample,
)
from slidetap.model import (
    Attribute,
    AttributeSchema,
    AttributeValidation,
    CodeAttribute,
    CodeAttributeSchema,
    DatetimeAttribute,
    DatetimeAttributeSchema,
    EnumAttribute,
    EnumAttributeSchema,
    Item,
    ItemValidation,
    ListAttribute,
    ListAttributeSchema,
    MeasurementAttribute,
    MeasurementAttributeSchema,
    NumericAttribute,
    NumericAttributeSchema,
    ObjectAttribute,
    ObjectAttributeSchema,
    Project,
    ProjectValidation,
    RelationValidation,
    StringAttribute,
    StringAttributeSchema,
    UnionAttribute,
    UnionAttributeSchema,
)
from slidetap.services.database_service import DatabaseService
from slidetap.services.schema_service import SchemaService


class ValidationService:
    def __init__(
        self, schema_service: SchemaService, database_service: DatabaseService
    ):
        self._schema_service = schema_service
        self._database_service = database_service

    def validate_item_relations(self, item: Union[UUID, Item, DatabaseItem]):
        item = self._database_service.get_item(item)
        return self._validate_item_relations(item)

    def validate_project(
        self, project: Union[UUID, Project, DatabaseProject]
    ) -> Optional[ProjectValidation]:
        project = self._database_service.get_project(project)
        return self._validate_project(project)

    def validate_item(
        self, item: Union[UUID, Item, DatabaseItem]
    ) -> Optional[ItemValidation]:
        item = self._database_service.get_item(item)
        return self._validate_item(item)

    def validate_attribute(self, attribute: Union[Attribute, DatabaseAttribute, UUID]):
        attribute = self._database_service.get_attribute(attribute)
        attribute_schema = self._schema_service.get_attribute(attribute.schema_uid)
        return self._validate_database_attribute(attribute, attribute_schema)

    def validate_attributes_for_item(self, item: Union[UUID, Item, DatabaseItem]):
        item = self._database_service.get_item(item)
        item.valid_attributes = all(
            attribute.valid for attribute in item.iterate_attributes()
        )

    def validate_attributes_for_project(
        self, project: Union[UUID, Project, DatabaseProject]
    ):
        project = self._database_service.get_project(project)
        project.valid_attributes = all(
            attribute.valid for attribute in project.iterate_attributes()
        )

    def get_validation_for_item(
        self, item: Union[UUID, Item, DatabaseItem]
    ) -> ItemValidation:
        item = self._database_service.get_item(item)
        return self._get_validation_for_item(item)

    def get_validation_for_project(
        self, project: Union[UUID, Project, DatabaseProject]
    ) -> ProjectValidation:
        project = self._database_service.get_project(project)
        return self._get_validation_for_project(project)

    def get_validation_for_attribute(
        self, attribute: Union[UUID, Attribute, DatabaseAttribute]
    ) -> AttributeValidation:
        attribute = self._database_service.get_attribute(attribute)
        return self._get_validation_for_attribute(attribute)

    def _get_validation_for_item(self, item: DatabaseItem) -> ItemValidation:
        attribute_validations = (
            self._get_validation_for_attribute(attribute)
            for attribute in item.attributes.values()
        )
        relation_validations = self._validate_item_relations(item)
        return self._build_item_validation(
            item, relation_validations, attribute_validations
        )

    def _get_validation_for_project(
        self, project: DatabaseProject
    ) -> ProjectValidation:
        items = self._database_service.get_project_items(project.uid)
        item_validations = (self._get_validation_for_item(item) for item in items)
        attribute_validations = (
            self._get_validation_for_attribute(attribute)
            for attribute in project.iterate_attributes()
        )
        return self._build_project_validation(
            project, item_validations, attribute_validations
        )

    def _get_validation_for_attribute(
        self, attribute: DatabaseAttribute
    ) -> AttributeValidation:
        attribute_schema = self._schema_service.get_attribute(attribute.schema_uid)
        return AttributeValidation(
            attribute.valid, attribute.uid, attribute_schema.display_name
        )

    def _validate_project(self, project: DatabaseProject) -> ProjectValidation:
        attribute_validation = self._validate_database_attributes(
            project.attributes, self._schema_service.root.project.attributes.values()
        )
        items = self._database_service.get_project_items(project.uid)
        item_validations = [self._validate_item(item) for item in items]
        validation = self._build_project_validation(
            project, item_validations, attribute_validation
        )
        project.valid_attributes = len(validation.non_valid_attributes) == 0
        project.valid_items = len(validation.non_valid_items) == 0
        return validation

    def _validate_item(self, item: DatabaseItem) -> ItemValidation:
        relation_validations = self._validate_item_relations(item)
        attribute_validations = self._validate_database_attributes(
            item.attributes,
            self._schema_service.items[item.schema_uid].attributes.values(),
        )
        validation = self._build_item_validation(
            item, relation_validations, attribute_validations
        )
        item.valid_attributes = len(validation.non_valid_attributes) == 0
        item.valid_relations = len(validation.non_valid_relations) == 0
        return validation

    def _validate_database_attribute(
        self, attribute: Optional[DatabaseAttribute], schema: AttributeSchema
    ):
        if attribute is None:
            return AttributeValidation(schema.optional, schema.uid, schema.display_name)
        validation = self._validate_attribute(attribute.model, schema)
        attribute.valid = validation.valid
        return validation

    def _validate_database_attributes(
        self,
        attributes: Dict[str, DatabaseAttribute],
        schemas: Iterable[AttributeSchema],
    ) -> List[AttributeValidation]:
        return [
            self._validate_database_attribute(attributes.get(schema.tag), schema)
            for schema in schemas
        ]

    def _validate_attribute(
        self, attribute: Attribute, schema: AttributeSchema
    ) -> AttributeValidation:
        if isinstance(attribute, StringAttribute) and isinstance(
            schema, StringAttributeSchema
        ):
            valid = (
                attribute.value is not None and attribute.value != ""
            ) or schema.optional
            return AttributeValidation(valid, attribute.uid, schema.display_name)
        if isinstance(attribute, EnumAttribute) and isinstance(
            schema, EnumAttributeSchema
        ):
            valid = (
                (
                    attribute.value is not None
                    and attribute.value != ""
                    and attribute.value in schema.allowed_values
                )
                or attribute.value is None
                and schema.optional
            )
            return AttributeValidation(valid, attribute.uid, schema.display_name)
        if isinstance(attribute, DatetimeAttribute) and isinstance(
            schema, DatetimeAttributeSchema
        ):
            # TODO check if datetime, date, or time?
            valid = attribute.value is not None or schema.optional
            return AttributeValidation(valid, attribute.uid, schema.display_name)
        if isinstance(attribute, NumericAttribute) and isinstance(
            schema, NumericAttributeSchema
        ):
            # TODO Check if int?
            valid = (attribute.value is not None) or schema.optional
            return AttributeValidation(valid, attribute.uid, schema.display_name)
        if isinstance(attribute, MeasurementAttribute) and isinstance(
            schema, MeasurementAttributeSchema
        ):
            valid = (
                attribute.value is not None
                and (
                    schema.allowed_units is None
                    or attribute.value.unit in schema.allowed_units
                )
            ) or (attribute.value is None and schema.optional)
            return AttributeValidation(valid, attribute.uid, schema.display_name)
        if isinstance(attribute, CodeAttribute) and isinstance(
            schema, CodeAttributeSchema
        ):
            valid = (
                attribute.value is not None
                and (
                    schema.allowed_schemas is None
                    or attribute.value.scheme in schema.allowed_schemas
                )
            ) or (attribute.value is None and schema.optional)
            return AttributeValidation(valid, attribute.uid, schema.display_name)
        if isinstance(attribute, ObjectAttribute) and isinstance(
            schema, ObjectAttributeSchema
        ):
            if attribute.value is None or len(attribute.value) == 0:
                return AttributeValidation(
                    schema.optional, attribute.uid, schema.display_name
                )
            validations: List[AttributeValidation] = []
            for tag, attribue_schema in schema.attributes.items():
                if tag not in attribute.value:
                    validations.append(
                        AttributeValidation(
                            attribue_schema.optional, attribute.uid, schema.display_name
                        )
                    )
                else:
                    attribute_validation = self._validate_attribute(
                        attribute.value[tag], attribue_schema
                    )
                    validations.append(attribute_validation)
            valid = all(validation.valid for validation in validations)
            return AttributeValidation(valid, attribute.uid, schema.display_name)
        if isinstance(attribute, ListAttribute) and isinstance(
            schema, ListAttributeSchema
        ):
            if attribute.value is None or len(attribute.value) == 0:
                return AttributeValidation(
                    schema.optional, attribute.uid, schema.display_name
                )
            validations = [
                self._validate_attribute(value, schema.attribute)
                for value in attribute.value
            ]
            valid = all(validation.valid for validation in validations)
            return AttributeValidation(valid, attribute.uid, schema.display_name)
        if isinstance(attribute, UnionAttribute) and isinstance(
            schema, UnionAttributeSchema
        ):
            if attribute.value is None:
                return AttributeValidation(
                    schema.optional, attribute.uid, schema.display_name
                )
            return self._validate_attribute(
                attribute.value,
                next(
                    schema
                    for schema in schema.attributes
                    if schema.uid == attribute.value.schema_uid
                ),
            )
        raise ValueError(f"Attribute {attribute} is not a valid attribute type.")

    def _validate_item_relations(
        self, item: DatabaseItem
    ) -> Iterable[RelationValidation]:
        if isinstance(item, DatabaseAnnotation):
            return self._validate_annotation_relations(item)
        if isinstance(item, DatabaseObservation):
            return self._validate_observation_relations(item)
        if isinstance(item, DatabaseImage):
            return self._validate_image_relations(item)
        if isinstance(item, DatabaseSample):
            return self._validate_sample_relations(item)
        raise ValueError(f"Item {item} is not a valid item type.")

    def _validate_annotation_relations(
        self, annotation: DatabaseAnnotation, other_side: bool = True
    ) -> Iterable[RelationValidation]:
        schema = self._schema_service.annotations[annotation.schema_uid]
        if annotation.image is not None and annotation.image.selected:
            current_app.logger.debug(
                f"Valid relation for annotation {annotation.uid} to image {annotation.image.uid}."
            )
            relation = next(
                relation
                for relation in schema.images
                if relation.image.uid == annotation.image.schema_uid
            )
            annotation.valid_relations = True
            if other_side:
                current_app.logger.debug(
                    f"Validation relations for image {annotation.image.uid} as other side of annotation {annotation.uid}."
                )
                self._validate_image_relations(annotation.image, other_side=False)
            return [RelationValidation(True, relation.uid, relation.name)]
        current_app.logger.debug(f"No valid relation for annotation {annotation.uid}.")
        annotation.valid_relations = False
        return [
            RelationValidation(False, relation.uid, relation.name)
            for relation in schema.images
        ]

    def _validate_observation_relations(
        self, observation: DatabaseObservation, other_side: bool = True
    ) -> Iterable[RelationValidation]:
        relation = None
        schema = self._schema_service.observations[observation.schema_uid]

        if observation.image is not None and observation.image.selected:
            current_app.logger.debug(
                f"Valid relation for observation {observation.uid} to image {observation.image.uid}."
            )
            relation = next(
                relation
                for relation in schema.images
                if relation.image.uid == observation.image.schema_uid
            )
            if other_side:
                current_app.logger.debug(
                    f"Validation relations for image {observation.image.uid} as other side of observation {observation.uid}."
                )
                self._validate_image_relations(observation.image, other_side=False)
        elif observation.sample is not None and observation.sample.selected:
            current_app.logger.debug(
                f"Valid relation for observation {observation.uid} to sample {observation.sample.uid}."
            )
            relation = next(
                relation
                for relation in schema.samples
                if relation.sample.uid == observation.sample.schema_uid
            )
            if other_side:
                current_app.logger.debug(
                    f"Validation relations for sample {observation.sample.uid} as other side of observation {observation.uid}."
                )
                self._validate_sample_relations(observation.sample, other_side=False)

        elif observation.annotation is not None and observation.annotation.selected:
            current_app.logger.debug(
                f"Valid relation for observation {observation.uid} to annotation {observation.annotation.uid}."
            )
            relation = next(
                relation
                for relation in schema.annotations
                if relation.annotation.uid == observation.annotation.schema_uid
            )
            if other_side:
                current_app.logger.debug(
                    f"Validation relations for annotation {observation.annotation.uid} as other side of observation {observation.uid}."
                )
                self._validate_annotation_relations(
                    observation.annotation, other_side=False
                )
        if relation is not None:
            observation.valid_relations = True
            return [RelationValidation(True, relation.uid, relation.name)]
        current_app.logger.debug(
            f"No valid relation for observation {observation.uid}."
        )
        observation.valid_relations = False
        return [
            RelationValidation(False, relation.uid, relation.name)
            for relation in schema.images + schema.samples + schema.annotations
        ]

    def _validate_image_relations(
        self, image: DatabaseImage, other_side: bool = True
    ) -> Iterable[RelationValidation]:
        schema = self._schema_service.images[image.schema_uid]
        if image.samples is not None and len(image.samples) > 0:
            current_app.logger.debug(
                f"Valid relation for image {image.uid} to samples {[sample.uid for sample in image.samples]}."
            )
            validations = set(
                [
                    RelationValidation(True, relation.uid, relation.name)
                    for relation in [
                        next(
                            relation
                            for relation in schema.samples
                            if relation.image.uid == sample.schema_uid
                        )
                        for sample in image.samples
                        if sample.selected
                    ]
                ]
            )
            if other_side:
                current_app.logger.debug(
                    f"Validation relations for samples {[sample.uid for sample in image.samples]} as other side of image {image.uid}."
                )
                for sample in image.samples:
                    self._validate_sample_relations(sample, other_side=False)
        else:
            current_app.logger.debug(
                f"No valid relation for image {image.uid} to samples."
            )
            validations = [
                RelationValidation(False, relation.uid, relation.name)
                for relation in schema.samples
            ]

        image.valid_relations = all(relation.valid for relation in validations)
        return validations

    def _validate_sample_relations(
        self, sample: DatabaseSample, other_side: bool = True
    ) -> Iterable[RelationValidation]:
        relations: List[RelationValidation] = []
        schema = self._schema_service.samples[sample.schema_uid]
        for relation in schema.children:
            children_of_type = self._database_service.get_sample_children(
                sample, relation.child.uid
            )
            selected_children_count = len(
                [child for child in children_of_type if child.selected]
            )
            current_app.logger.debug(
                f"Validating relation for sample {sample.uid} to children {[child.uid for child in children_of_type]}."
            )
            if (
                relation.min_children is not None
                and selected_children_count < relation.min_children
            ) or (
                relation.max_children is not None
                and selected_children_count > relation.max_children
            ):
                relations.append(RelationValidation(False, relation.uid, relation.name))
            else:
                relations.append(RelationValidation(True, relation.uid, relation.name))
            if other_side:
                current_app.logger.debug(
                    f"Validation relations for children {[child.uid for child in children_of_type]} as other side of sample {sample.uid}."
                )
                for child in children_of_type:
                    self._validate_sample_relations(child, other_side=False)

        for relation in schema.parents:
            parents_of_type = self._database_service.get_sample_parents(
                sample, relation.parent.uid
            )
            selected_parent_count = len(
                [parent for parent in parents_of_type if parent.selected]
            )
            current_app.logger.debug(
                f"Validating relation for sample {sample.uid} to parents {[parent.uid for parent in parents_of_type]}."
            )

            if (
                relation.min_parents is not None
                and selected_parent_count < relation.min_parents
            ) or (
                relation.max_parents is not None
                and selected_parent_count > relation.max_parents
            ):
                relations.append(RelationValidation(False, relation.uid, relation.name))
            else:
                relations.append(RelationValidation(True, relation.uid, relation.name))
            if other_side:
                current_app.logger.debug(
                    f"Validation relations for parents {[parent.uid for parent in parents_of_type]} as other side of sample {sample.uid}."
                )
                for parent in parents_of_type:
                    self._validate_sample_relations(parent, other_side=False)
        for relation in schema.images:
            images_of_type = self._database_service.get_sample_images(
                sample, relation.image.uid
            )
            selected_images = len([image for image in images_of_type if image.selected])
            relations.append(
                RelationValidation(selected_images > 0, relation.uid, relation.name)
            )
            if other_side:
                for image in images_of_type:
                    self._validate_image_relations(image, other_side=False)
        sample.valid_relations = all(relation.valid for relation in relations)
        return relations

    def _build_project_validation(
        self,
        project: DatabaseProject,
        item_validations: Iterable[ItemValidation],
        attribute_validation: Iterable[AttributeValidation],
    ) -> ProjectValidation:
        non_valid_attributes = [
            attribute_validation
            for attribute_validation in attribute_validation
            if not attribute_validation.valid
        ]
        valid_attributes = len(non_valid_attributes) == 0
        non_valid_items = [
            item_validation
            for item_validation in item_validations
            if not item_validation.valid
        ]
        valid_items = len(non_valid_items) == 0
        project.valid_attributes = valid_attributes
        project.valid_items = valid_items
        return ProjectValidation(
            valid_attributes and valid_items,
            project.uid,
            non_valid_attributes,
            non_valid_items,
        )

    def _build_item_validation(
        self,
        item: DatabaseItem,
        relation_validations: Iterable[RelationValidation],
        attribute_validations: Iterable[AttributeValidation],
    ) -> ItemValidation:
        non_valid_relations = [
            relation_validation
            for relation_validation in relation_validations
            if not relation_validation.valid
        ]
        non_valid_attributes = [
            attribute_validation
            for attribute_validation in attribute_validations
            if not attribute_validation.valid
        ]
        valid_relations = len(non_valid_relations) == 0
        valid_attributes = len(non_valid_attributes) == 0
        return ItemValidation(
            valid_relations and valid_attributes,
            item.uid,
            item.identifier,
            non_valid_attributes,
            non_valid_relations,
        )
