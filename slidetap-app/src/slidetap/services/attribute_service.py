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

"""Service for accessing attributes."""

import logging
from collections.abc import Callable, Iterable, Mapping, MutableMapping, Sequence
from typing import overload
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from slidetap.database import (
    DatabaseAttribute,
    DatabaseDataset,
    DatabaseItem,
    DatabaseProject,
)
from slidetap.model import (
    AnyAttribute,
    Attribute,
    AttributePath,
    AttributeSchema,
    BooleanAttribute,
    BooleanAttributeSchema,
    CodeAttribute,
    CodeAttributeSchema,
    Dataset,
    DatetimeAttribute,
    DatetimeAttributeSchema,
    EnumAttribute,
    EnumAttributeSchema,
    Item,
    ListAttribute,
    ListAttributeSchema,
    MeasurementAttribute,
    MeasurementAttributeSchema,
    NumericAttribute,
    NumericAttributeSchema,
    ObjectAttribute,
    ObjectAttributeSchema,
    Project,
    StringAttribute,
    StringAttributeSchema,
    UnionAttribute,
    UnionAttributeSchema,
)
from slidetap.services.database_service import DatabaseService
from slidetap.services.review_service import ReviewService
from slidetap.services.schema_service import SchemaService
from slidetap.services.validation_service import ValidationService


class AttributeService:
    """Attribute service should be used to interface with attributes"""

    def __init__(
        self,
        schema_service: SchemaService,
        validation_service: ValidationService,
        database_service: DatabaseService,
        review_service: ReviewService,
    ):
        self._schema_service = schema_service
        self._validation_service = validation_service
        self._database_service = database_service
        self._review_service = review_service
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def _validate_item_and_report(self, item_uid: UUID, session: Session) -> None:
        """Validate the item an edited attribute belongs to, and report it if
        that moved it between valid and not.

        An attribute is edited through here without the item it belongs to
        being saved, so this is the only place that notices what a curator
        filling one in did to the item.
        """
        was_valid = self._validation_service.item_is_valid_for_now(item_uid, session)
        self._validation_service.validate_item_attributes(item_uid, session)
        self._review_service.item_validity_changed(
            item_uid,
            was_valid,
            self._validation_service.item_is_valid_for_now(item_uid, session),
            session=session,
        )

    def get(self, attribute_uid: UUID) -> AnyAttribute:
        with self._database_service.get_session() as session:
            return self._database_service.get_attribute(session, attribute_uid).model

    def get_optional(self, attribute_uid: UUID) -> AnyAttribute | None:
        with self._database_service.get_session() as session:
            attribute = self._database_service.get_optional_attribute(
                session, attribute_uid
            )
            return attribute.model if attribute is not None else None

    def get_for_schema(self, attribute_schema_uid: UUID) -> Iterable[AnyAttribute]:
        with self._database_service.get_session() as session:
            attributes = self._database_service.get_attributes_for_schema(
                session, attribute_schema_uid
            )
            return [attribute.model for attribute in attributes]

    def update(
        self,
        attribute: Attribute,
        validate: bool = True,
        session: Session | None = None,
    ) -> AnyAttribute:
        with self._database_service.get_session(session) as session:
            existing_attribute = self._database_service.get_attribute(
                session, attribute.uid
            )
            if existing_attribute is None:
                raise ValueError(f"Attribute with uid {attribute.uid} does not exist")
            self._assert_can_edit(session, existing_attribute)
            self.set_display_value(attribute)
            existing_attribute.set_value(
                attribute.updated_value, attribute.display_value
            )
            existing_attribute.set_mapping_item_uid(attribute.mapping_item_uid)
            existing_attribute.set_mapped_value(attribute.mapped_value)
            existing_attribute.set_mappable_value(attribute.mappable_value)
            existing_attribute.set_rejected(attribute.rejected)
            self._database_service.record_unmapped_values(existing_attribute, session)
            if validate:
                self._validation_service.validate_attribute(existing_attribute, session)
                if existing_attribute.attribute_item_uid is not None:
                    self._validate_item_and_report(
                        existing_attribute.attribute_item_uid, session
                    )
                elif existing_attribute.attribute_project_uid is not None:
                    self._validation_service.validate_project_attributes(
                        existing_attribute.attribute_project_uid, session
                    )
                elif existing_attribute.attribute_dataset_uid is not None:
                    self._validation_service.validate_dataset_attributes(
                        existing_attribute.attribute_dataset_uid, session
                    )
            return existing_attribute.model

    def update_for_item(
        self,
        item: UUID | Item | DatabaseItem,
        attributes: Iterable[AnyAttribute],
        session: Session | None = None,
    ) -> None:
        with self._database_service.get_session(session) as session:
            item = self._database_service.get_item(session, item)
            held_by_schema = self._held_by_schema(item.attributes)
            for attribute in attributes:
                self.set_display_value(attribute)
                database_attribute = self._database_service.get_optional_attribute(
                    session, attribute.uid
                )
                if database_attribute is None:
                    database_attribute = self._replace_or_add(
                        attribute,
                        held_by_schema,
                        self._schema_service.get_attribute,
                        session,
                    )
                    item.attributes.add(database_attribute)
                else:
                    database_attribute.set_value(
                        attribute.updated_value, attribute.display_value
                    )
                    database_attribute.set_mappable_value(attribute.mappable_value)
                    database_attribute.set_rejected(attribute.rejected)
                    self._database_service.record_unmapped_values(
                        database_attribute, session
                    )
                self._validation_service.validate_attribute(database_attribute, session)
            self._validate_item_and_report(item.uid, session)

    def update_for_project(
        self,
        project: UUID | Project | DatabaseProject,
        attributes: Iterable[AnyAttribute],
    ) -> None:
        with self._database_service.get_session() as session:
            project = self._database_service.get_project(session, project)
            self._schema_service.assert_can_change(project, session)
            for attribute in attributes:
                self.set_display_value(attribute)
                database_attribute = self._database_service.get_attribute(
                    session, attribute.uid
                )
                database_attribute.set_value(
                    attribute.updated_value, attribute.display_value
                )
                database_attribute.set_mappable_value(attribute.mappable_value)
                database_attribute.set_rejected(attribute.rejected)
                self._validation_service.validate_attribute(database_attribute, session)
            self._validation_service.validate_project_attributes(project.uid, session)

    def update_for_dataset(
        self,
        dataset: UUID | Dataset | DatabaseDataset,
        attributes: Iterable[AnyAttribute],
    ) -> None:
        with self._database_service.get_session() as session:
            dataset = self._database_service.get_dataset(session, dataset)
            self._schema_service.assert_can_change(dataset, session)
            for attribute in attributes:
                self.set_display_value(attribute)

                database_attribute = self._database_service.get_attribute(
                    session, attribute.uid
                )
                database_attribute.set_value(
                    attribute.updated_value, attribute.display_value
                )
                database_attribute.set_mappable_value(attribute.mappable_value)
                database_attribute.set_rejected(attribute.rejected)
                self._validation_service.validate_attribute(database_attribute, session)
            self._validation_service.validate_dataset_attributes(dataset, session)

    def create(
        self,
        attribute: Attribute,
    ) -> AnyAttribute:
        with self._database_service.get_session() as session:
            created_attribute = self._database_service.add_attribute(
                session,
                attribute,
                self._schema_service.get_attribute(attribute.schema_uid),
            )
            self._assert_can_edit(session, created_attribute)
            self._validation_service.validate_attribute(created_attribute, session)
            if created_attribute.attribute_item_uid is not None:
                self._validate_item_and_report(
                    created_attribute.attribute_item_uid, session
                )
            elif created_attribute.attribute_project_uid is not None:
                self._validation_service.validate_project_attributes(
                    created_attribute.attribute_project_uid, session
                )
            elif created_attribute.attribute_dataset_uid is not None:
                self._validation_service.validate_dataset_attributes(
                    created_attribute.attribute_dataset_uid, session
                )
            return created_attribute.model

    def _assert_can_edit(self, session: Session, attribute: DatabaseAttribute) -> None:
        """Refuse changing an attribute of a project that cannot be edited."""
        self._schema_service.assert_can_change(attribute, session)

    def create_or_update_attributes(
        self,
        attributes: Iterable[AnyAttribute],
        session: Session | None = None,
        existing: MutableMapping[UUID, DatabaseAttribute] | None = None,
        held: Iterable[DatabaseAttribute] = (),
    ) -> list[DatabaseAttribute]:
        """Store attributes, updating those already stored.

        Parameters
        ----------
        existing: MutableMapping[UUID, DatabaseAttribute] | None
            Attributes already stored, by uid, for this call to read instead of
            looking its own up. Given by a caller storing a group, which looks
            the whole group up at once.

            What this call creates is deliberately not added to it. An importer
            is free to hand over attributes carrying a placeholder uid, and
            more than one of them may carry the same one, so an attribute is
            matched only against what was stored before the group began -- as
            it was when each was looked up on its own.
        held: Iterable[DatabaseAttribute]
            The attributes the owner the attributes are stored for holds now.
            An attribute whose uid is not stored, given for a schema the owner
            holds an attribute of, replaces that attribute in its row, see
            :py:meth:`DatabaseAttribute.replace_values`. The owner holds one
            attribute of each schema, so a row beside it would be refused.
        """
        with self._database_service.get_session(session) as session:
            return self._create_or_update_attributes(
                attributes, session, existing, held
            )

    def create_or_update_private_attributes(
        self,
        attributes: Iterable[AnyAttribute],
        session: Session | None = None,
        existing: MutableMapping[UUID, DatabaseAttribute] | None = None,
        held: Iterable[DatabaseAttribute] = (),
    ) -> list[DatabaseAttribute]:
        """Store private attributes, see
        :py:meth:`create_or_update_attributes`."""
        with self._database_service.get_session(session) as session:
            return self._create_or_update_private_attributes(
                attributes, session, existing, held
            )

    def _create_or_update_attributes(
        self,
        attributes: Iterable[AnyAttribute],
        session: Session,
        existing: MutableMapping[UUID, DatabaseAttribute] | None = None,
        held: Iterable[DatabaseAttribute] = (),
    ) -> list[DatabaseAttribute]:
        attributes = list(attributes)
        # Looked up as a group rather than one at a time: an item carries
        # hundreds of attributes, and each lookup that stands on its own is a
        # round trip -- and a query here writes out whatever is waiting to be
        # written, which is what a caller storing a group is trying to defer.
        if existing is None:
            existing = self._database_service.get_optional_attributes(
                session, attributes
            )
        held_by_schema = self._held_by_schema(held)
        database_attributes: list[DatabaseAttribute] = []
        for attribute in attributes:
            self.set_display_value(attribute)
            database_attribute = existing.get(attribute.uid)
            if database_attribute:
                database_attribute.set_value(attribute.value, attribute.display_value)
            else:
                database_attribute = self._replace_or_add(
                    attribute,
                    held_by_schema,
                    self._schema_service.get_attribute,
                    session,
                )

            database_attributes.append(database_attribute)
        return database_attributes

    def _create_or_update_private_attributes(
        self,
        attributes: Iterable[AnyAttribute],
        session: Session,
        existing: MutableMapping[UUID, DatabaseAttribute] | None = None,
        held: Iterable[DatabaseAttribute] = (),
    ) -> list[DatabaseAttribute]:
        attributes = list(attributes)
        if existing is None:
            existing = self._database_service.get_optional_attributes(
                session, attributes
            )
        held_by_schema = self._held_by_schema(held)
        database_attributes: list[DatabaseAttribute] = []
        for attribute in attributes:
            self.set_display_value(attribute)
            database_attribute = existing.get(attribute.uid)

            if database_attribute:
                database_attribute.set_value(attribute.value, attribute.display_value)
            else:
                database_attribute = self._replace_or_add(
                    attribute,
                    held_by_schema,
                    self._schema_service.get_private_attribute,
                    session,
                )
            database_attributes.append(database_attribute)
        return database_attributes

    @staticmethod
    def _held_by_schema(
        held: Iterable[DatabaseAttribute],
    ) -> dict[UUID, DatabaseAttribute]:
        """The attributes an owner holds, by attribute schema."""
        return {held_attribute.schema_uid: held_attribute for held_attribute in held}

    def _replace_or_add(
        self,
        attribute: AnyAttribute,
        held_by_schema: Mapping[UUID, DatabaseAttribute],
        get_schema: Callable[[UUID], AttributeSchema],
        session: Session,
    ) -> DatabaseAttribute:
        """Store an attribute whose uid is not stored.

        Written over the attribute the owner holds of its schema where there is
        one, keeping that row and its uid, and added as a row of its own where
        there is none.
        """
        held_attribute = held_by_schema.get(attribute.schema_uid)
        if held_attribute is None:
            return self._database_service.add_attribute(
                session, attribute, get_schema(attribute.schema_uid)
            )
        held_attribute.replace_values(attribute)
        self._database_service.record_unmapped_values(held_attribute, session)
        return held_attribute

    def set_display_value(self, attribute: Attribute) -> None:
        """Set ``attribute.display_value`` from its schema's renderer.

        Public so callers in other services (e.g. ``MapperService``) can
        compute the same display string instead of duplicating the logic.
        """
        schema = self._schema_service.get_any_attribute(attribute.schema_uid)
        if attribute.value is None:
            attribute.display_value = None
        else:
            attribute.display_value = schema.create_display_value(attribute.value)

    @staticmethod
    def resolve_attribute(
        attributes: dict[str, AnyAttribute],
        tag: str,
    ) -> AnyAttribute | None:
        """Resolve a possibly nested attribute tag from a Pydantic
        attribute dict. Supports compound ``parent.child`` tags by walking
        into the parent ObjectAttribute's effective value (updated > mapped
        > original).
        """
        if tag in attributes:
            return attributes[tag]
        parent_tag, _, child_tag = tag.partition(".")
        if not child_tag:
            return None
        parent_attr = attributes.get(parent_tag)
        if not isinstance(parent_attr, ObjectAttribute):
            return None
        for value_dict in (
            parent_attr.updated_value,
            parent_attr.mapped_value,
            parent_attr.original_value,
        ):
            if value_dict and child_tag in value_dict:
                return value_dict[child_tag]
        return None

    @overload
    @staticmethod
    def empty_attribute_from_schema(
        schema: StringAttributeSchema,
    ) -> StringAttribute: ...
    @overload
    @staticmethod
    def empty_attribute_from_schema(
        schema: EnumAttributeSchema,
    ) -> EnumAttribute: ...
    @overload
    @staticmethod
    def empty_attribute_from_schema(
        schema: DatetimeAttributeSchema,
    ) -> DatetimeAttribute: ...
    @overload
    @staticmethod
    def empty_attribute_from_schema(
        schema: NumericAttributeSchema,
    ) -> NumericAttribute: ...
    @overload
    @staticmethod
    def empty_attribute_from_schema(
        schema: MeasurementAttributeSchema,
    ) -> MeasurementAttribute: ...
    @overload
    @staticmethod
    def empty_attribute_from_schema(
        schema: CodeAttributeSchema,
    ) -> CodeAttribute: ...
    @overload
    @staticmethod
    def empty_attribute_from_schema(
        schema: BooleanAttributeSchema,
    ) -> BooleanAttribute: ...
    @overload
    @staticmethod
    def empty_attribute_from_schema(
        schema: ObjectAttributeSchema,
    ) -> ObjectAttribute: ...
    @overload
    @staticmethod
    def empty_attribute_from_schema(
        schema: ListAttributeSchema,
    ) -> ListAttribute: ...
    @overload
    @staticmethod
    def empty_attribute_from_schema(
        schema: UnionAttributeSchema,
    ) -> UnionAttribute: ...
    @staticmethod
    def empty_attribute_from_schema(schema: AttributeSchema) -> AnyAttribute:
        """Construct an empty attribute matching ``schema``.

        Used when creating new items so the schema-defined attribute
        structure exists immediately. Without this, freshly-created items
        have no attributes at all and editors that reach into nested
        ObjectAttributes (e.g. ``statement.diagnose``) have nothing to
        merge into.

        Children of ObjectAttributes are not pre-materialised — clients
        render placeholders for missing children from the schema and the
        deep-merge on save fills them in.
        """
        base = {
            "uid": uuid4(),
            "schema_uid": schema.uid,
            "valid": schema.optional or schema.default_value is not None,
        }
        if schema.default_value is not None:
            # As the original value rather than an update: nobody typed it, and
            # reverting an edit should come back to it.
            base["original_value"] = schema.default_value
            base["display_value"] = schema.create_display_value(schema.default_value)
        if isinstance(schema, StringAttributeSchema):
            return StringAttribute(**base)
        if isinstance(schema, EnumAttributeSchema):
            return EnumAttribute(**base)
        if isinstance(schema, DatetimeAttributeSchema):
            return DatetimeAttribute(**base)
        if isinstance(schema, NumericAttributeSchema):
            return NumericAttribute(**base)
        if isinstance(schema, MeasurementAttributeSchema):
            return MeasurementAttribute(**base)
        if isinstance(schema, CodeAttributeSchema):
            return CodeAttribute(**base)
        if isinstance(schema, BooleanAttributeSchema):
            return BooleanAttribute(**base)
        if isinstance(schema, ObjectAttributeSchema):
            # The exception to leaving children out: one with a default is one
            # nobody is going to type, so if it is not built here it is never
            # there at all.
            defaulted = {
                tag: AttributeService.empty_attribute_from_schema(child)
                for tag, child in schema.attributes.items()
                if child.default_value is not None
            }
            if defaulted and base.get("original_value") is None:
                base["original_value"] = defaulted
            return ObjectAttribute(**base)
        if isinstance(schema, ListAttributeSchema):
            return ListAttribute(**base)
        if isinstance(schema, UnionAttributeSchema):
            return UnionAttribute(**base)
        raise TypeError(f"Unknown attribute schema type {type(schema).__name__}.")

    def move_attribute_value(
        self,
        source: DatabaseItem,
        source_path: Sequence[str | int],
        target: DatabaseItem,
        target_path: Sequence[str | int],
        session: Session,
    ) -> None:
        """Move the value at the end of a path on one item to the end of a path
        on another, or on the same item.

        A path on an item is the tag of an attribute of the item, then the tags
        of the attributes in objects and the positions of the attributes in
        lists it goes down through, such as ``["statement", "diagnoses", 2]``.

        Where the target holds a value, the two are swapped. Where it holds none,
        the value is moved there, leaving the source without it: an attribute
        of an object left empty, or, past the last of a list, appended to it.
        A value taken out of a list leaves no gap.

        Both paths lead to attributes of the same schema, held by attributes of
        the same schema, such as two entries of the same list on items of
        different kinds. The values are moved whole, with what was mapped and
        what is still to be mapped of them. An attribute held in another is
        moved as an edit of what holds it, which keeps what was imported as it
        came. See `AttributePath`.

        Raises
        ------
        ValueError
            If a path does not start with a tag of an attribute of its item,
            goes through something that is not an object or a list, the source
            holds no value, or the paths do not lead to the same kind of
            attribute.
        """
        source_tag, source_attribute_path = AttributePath.from_item_path(source_path)
        target_tag, target_attribute_path = AttributePath.from_item_path(target_path)
        if bool(source_attribute_path.steps) != bool(target_attribute_path.steps):
            raise ValueError(
                f"Cannot move between attribute '{source_tag}' and attribute "
                f"'{target_tag}': one path is a whole attribute, the other a value "
                "inside one."
            )
        if not source_attribute_path.steps:
            if source_tag != target_tag:
                raise ValueError(
                    f"Cannot move attribute '{source_tag}' to attribute '{target_tag}'."
                )
            self._swap_attribute_values(source, target, source_tag, session)
            return
        source_row = self._find_top_level_attribute(source, source_tag)
        target_row = self._find_top_level_attribute(target, target_tag)
        if source_row is None or target_row is None:
            raise ValueError(
                f"Attribute '{source_tag}' or '{target_tag}' missing on source or "
                "target"
            )
        same_row = source_row is target_row
        source_root = source_row.model
        target_root = source_root if same_row else target_row.model
        self._schema_service.assert_paths_hold_same_kind(
            source_root.schema_uid,
            source_attribute_path,
            target_root.schema_uid,
            target_attribute_path,
        )
        source_root_schema = self._schema_service.get_any_attribute(
            source_root.schema_uid
        )
        target_root_schema = self._schema_service.get_any_attribute(
            target_root.schema_uid
        )
        moved = source_attribute_path.value_in(source_root)
        if moved is None:
            raise ValueError(f"No value at {list(source_path)} to move.")
        replaced = target_attribute_path.value_in(target_root)

        if same_row:
            if source_attribute_path.overlaps(target_attribute_path):
                raise ValueError("Cannot move a value into or out of itself.")
            root = source_attribute_path.replaced_in(
                source_root, source_root_schema, replaced
            )
            if replaced is None:
                # Taken out first, what was after it in its list moves up.
                target_attribute_path = target_attribute_path.after_removal_of(
                    source_attribute_path
                )
            root = target_attribute_path.replaced_in(root, source_root_schema, moved)
            source_row.set_value(root.updated_value, root.display_value)
        else:
            source_root = source_attribute_path.replaced_in(
                source_root, source_root_schema, replaced
            )
            target_root = target_attribute_path.replaced_in(
                target_root, target_root_schema, moved
            )
            source_row.set_value(source_root.updated_value, source_root.display_value)
            target_row.set_value(target_root.updated_value, target_root.display_value)
        self._record_unmapped_on_both(source_row, target_row, session)

    def _swap_attribute_values(
        self,
        source: DatabaseItem,
        target: DatabaseItem,
        attribute_tag: str,
        session: Session,
    ) -> None:
        """Exchange the values of the top-level attribute of a tag between two
        items: what was edited, mapped, and is still to be mapped of it, and
        its display value. What was imported stays on each, as it came.

        Raises
        ------
        ValueError
            If either item has no attribute of the tag.
        """
        source_attr = self._find_top_level_attribute(source, attribute_tag)
        target_attr = self._find_top_level_attribute(target, attribute_tag)
        if source_attr is None or target_attr is None:
            raise ValueError(f"Attribute '{attribute_tag}' missing on source or target")
        source_attr.updated_value, target_attr.updated_value = (
            target_attr.updated_value,
            source_attr.updated_value,
        )
        source_attr.mapped_value, target_attr.mapped_value = (
            target_attr.mapped_value,
            source_attr.mapped_value,
        )
        source_attr.mappable_value, target_attr.mappable_value = (
            target_attr.mappable_value,
            source_attr.mappable_value,
        )
        source_attr.display_value, target_attr.display_value = (
            target_attr.display_value,
            source_attr.display_value,
        )
        self._record_unmapped_on_both(source_attr, target_attr, session)

    def _record_unmapped_on_both(
        self,
        source_attr: DatabaseAttribute,
        target_attr: DatabaseAttribute,
        session: Session,
    ) -> None:
        """Say again, for both ends, which of their values wait for a mapping.

        Exchanging the values exchanges which of them is mapped, and the record
        of what is waiting is kept per attribute. Without this it would go on
        naming the one that no longer holds the value, and the count of items a
        mapping key would settle would be wrong for both.
        """
        for attribute in (source_attr, target_attr):
            self._database_service.record_unmapped_values(attribute, session)

    @staticmethod
    def _find_top_level_attribute(
        item: DatabaseItem, tag: str
    ) -> DatabaseAttribute | None:
        for attr in (*item.attributes, *item.private_attributes):
            if attr.tag == tag:
                return attr
        return None
