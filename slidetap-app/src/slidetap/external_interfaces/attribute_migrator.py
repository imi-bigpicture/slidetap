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

"""Copying an attribute to the attribute schema of another root."""

from collections.abc import Callable, Mapping, Sequence
from typing import Any, cast
from uuid import UUID

from slidetap.model import (
    AnyAttribute,
    AnyAttributeSchema,
    Attribute,
    AttributeSchema,
    AttributeValueType,
    ListAttributeSchema,
    ObjectAttributeSchema,
    UnionAttributeSchema,
)


class AttributeMigrator:
    """Copies an attribute to a target attribute schema, for migrations.

    What an attribute holds is kept: its three values, what it was left to map,
    what was refused of it, and how it is shown. What refers to a schema is
    moved: the schema uid of the attribute, and of every attribute nested in
    the JSON of its values. A nested attribute is moved to the attribute of the
    same tag in an object, to the attribute of a list, and to the member of the
    same value type in a union.

    The mapping item is kept, as the mapper of an attribute a migration moves
    is moved with it, see SchemaMigration.migrate_attribute.

    A helper for implementing a migration, for the attributes whose values
    are the same on the target root.
    """

    def migrate(self, attribute: AnyAttribute, target: AttributeSchema) -> AnyAttribute:
        """The attribute, copied to the target schema.

        Parameters
        ----------
        attribute: AnyAttribute
            The attribute to copy. Not changed.
        target: AttributeSchema
            The schema to copy it to, of the same value type.

        Returns
        -------
        AnyAttribute
            The copy, with the same uid.

        Raises
        ------
        ValueError
            If the target is of another value type, as the values of the
            attribute could not be held by it.
        """
        if attribute.attribute_value_type != self._value_type(target):
            raise ValueError(
                f"Cannot move attribute {attribute.uid} of value type "
                f"{attribute.attribute_value_type.name} to schema {target.uid} of "
                f"value type {self._value_type(target).name}."
            )
        update: dict[str, Any] = {
            "schema_uid": target.uid,
            "original_value": self._migrate_value(attribute.original_value, target),
            "updated_value": self._migrate_value(attribute.updated_value, target),
            "mapped_value": self._migrate_value(attribute.mapped_value, target),
        }
        return attribute.model_copy(update=update, deep=True)

    def _migrate_value(self, value: Any, target: AttributeSchema) -> Any:
        """A value of an attribute of the target schema, with what it nests
        moved to the target's nested schemas."""
        if value is None:
            return None
        if isinstance(target, ObjectAttributeSchema) and isinstance(value, Mapping):
            return {
                tag: self.migrate(nested, self._nested_of_object(target, tag))
                for tag, nested in value.items()
            }
        if isinstance(target, ListAttributeSchema) and isinstance(value, Sequence):
            return [self.migrate(nested, target.attribute) for nested in value]
        if isinstance(target, UnionAttributeSchema):
            return self.migrate(value, self._member_of_union(target, value))
        return value

    @staticmethod
    def _nested_of_object(target: ObjectAttributeSchema, tag: str) -> AttributeSchema:
        nested = target.attributes.get(tag)
        if nested is None:
            raise ValueError(
                f"Object attribute schema {target.uid} has no attribute {tag!r} to "
                f"move a nested attribute to."
            )
        return nested

    @staticmethod
    def _member_of_union(
        target: UnionAttributeSchema, value: AnyAttribute
    ) -> AttributeSchema:
        """The member a union's value is moved to: the one of its own schema
        where the target has it, else the first of its value type."""
        members = [
            member
            for member in target.attributes
            if AttributeMigrator._value_type(member) == value.attribute_value_type
        ]
        if not members:
            raise ValueError(
                f"Union attribute schema {target.uid} has no member of value type "
                f"{value.attribute_value_type.name}."
            )
        for member in members:
            if member.uid == value.schema_uid:
                return member
        return members[0]

    @staticmethod
    def _value_type(schema: AttributeSchema) -> AttributeValueType:
        """The value type of a schema, which every concrete schema declares."""
        return cast(AnyAttributeSchema, schema).attribute_value_type

    @classmethod
    def without_mapping_items(
        cls, attribute: AnyAttribute, removed: Callable[[UUID], bool]
    ) -> AnyAttribute:
        """The attribute with the mapping items that are removed referred to by
        nothing, its own and those of the attributes nested in its values.

        Parameters
        ----------
        attribute: AnyAttribute
            The attribute. Not changed.
        removed: Callable[[UUID], bool]
            Whether a mapping item is removed.

        Returns
        -------
        AnyAttribute
            A copy, with what was mapped kept and the mapping it was mapped by
            cleared where that is removed.
        """
        update: dict[str, Any] = {
            key: cls._value_without_mapping_items(getattr(attribute, key), removed)
            for key in ("original_value", "updated_value", "mapped_value")
        }
        if attribute.mapping_item_uid is not None and removed(
            attribute.mapping_item_uid
        ):
            update["mapping_item_uid"] = None
        return attribute.model_copy(update=update)

    @classmethod
    def _value_without_mapping_items(
        cls, value: Any, removed: Callable[[UUID], bool]
    ) -> Any:
        if isinstance(value, Attribute):
            return cls.without_mapping_items(cast(AnyAttribute, value), removed)
        if isinstance(value, Mapping):
            return {
                key: cls._value_without_mapping_items(nested, removed)
                for key, nested in value.items()
            }
        if isinstance(value, list | tuple):
            return [
                cls._value_without_mapping_items(nested, removed) for nested in value
            ]
        return value
