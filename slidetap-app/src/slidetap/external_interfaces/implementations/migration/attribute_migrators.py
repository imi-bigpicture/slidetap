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

"""The attribute migrators of a migration, by source attribute schema, and the
migrator moving an attribute that holds the same values with them."""

from collections.abc import Callable, Mapping, Sequence
from functools import partial
from typing import Any, cast
from uuid import UUID

from slidetap.external_interfaces.implementations.migration.attribute_migrator import (
    AttributeMigrator,
    MigratedAttribute,
)
from slidetap.model import (
    AnyAttribute,
    AnyAttributeSchema,
    AttributeSchema,
    AttributeValueType,
    ListAttributeSchema,
    ObjectAttributeSchema,
    UnionAttributeSchema,
)


class AttributeMigrators:
    """The attribute migrator and target attribute schema of each source
    attribute schema whose attributes change, registered one by one.

    A migration looks up an attribute here to migrate the attribute of a
    mapping item, and the target of an attribute schema to move a mapper to.
    An `UnchangedAttributeMigrator` created with the registry looks up here the
    attributes nested in those it moves.
    """

    def __init__(self):
        """Create the registry, empty."""
        self._migrators: dict[UUID, tuple[AttributeMigrator, AttributeSchema]] = {}

    def register(
        self,
        source: AttributeSchema,
        migrator: AttributeMigrator,
        target: AttributeSchema,
    ) -> None:
        """Register how the attributes of a source attribute schema migrate.

        Parameters
        ----------
        source: AttributeSchema
            The attribute schema of the source root.
        migrator: AttributeMigrator
            The migrator of its attributes.
        target: AttributeSchema
            The attribute schema of the target root they migrate to.

        Raises
        ------
        ValueError
            If the source attribute schema is registered already.
        """
        if source.uid in self._migrators:
            raise ValueError(
                f"Attribute schema {source.tag} ({source.uid}) is registered already."
            )
        self._migrators[source.uid] = (migrator, target)

    def register_unchanged(
        self, source: AttributeSchema, target: AttributeSchema
    ) -> None:
        """Register an attribute schema that holds the same values in the
        target root under other uids, with what it nests, to be moved as it is.

        The source and target schemas are walked side by side: the attributes
        of an object by tag, the attribute of a list, and the members of a
        union by position. Each attribute schema whose uid differs from that of
        its target, the source schema included, is registered with an
        `UnchangedAttributeMigrator` of this registry, which moves an attribute
        and migrates what it nests by the migrators registered here. An
        attribute schema registered already is kept, with what it nests, which
        its migrator migrates. One with the same uid as its target is moved as
        it is anyway and is not registered. Register the migrator of an
        attribute schema that changes in another way, such as an enum of other
        values, before.

        Parameters
        ----------
        source: AttributeSchema
            The attribute schema of the source root.
        target: AttributeSchema
            The attribute schema of the target root, of the same structure.

        Raises
        ------
        ValueError
            If the target is not of the same structure: an attribute schema of
            another kind, an object without an attribute of a tag, or a union
            of another number of members. Nothing is registered then.
        """
        pairs = self._pair_unchanged(source, target, source.tag)
        migrator = UnchangedAttributeMigrator(self)
        for source_schema, target_schema in pairs:
            self._migrators[source_schema.uid] = (migrator, target_schema)

    def get(self, schema_uid: UUID) -> tuple[AttributeMigrator, AttributeSchema] | None:
        """Get the migrator and target of a source attribute schema.

        Parameters
        ----------
        schema_uid: UUID
            The uid of the source attribute schema.

        Returns
        -------
        tuple[AttributeMigrator, AttributeSchema] | None
            The migrator and the target attribute schema, or None where the
            schema is not registered.
        """
        return self._migrators.get(schema_uid)

    def __contains__(self, schema_uid: object) -> bool:
        """Check if a source attribute schema uid is registered."""
        return schema_uid in self._migrators

    def _pair_unchanged(
        self, source: AttributeSchema, target: AttributeSchema, path: str
    ) -> list[tuple[AttributeSchema, AttributeSchema]]:
        """Pair a source attribute schema and what it nests with their targets,
        leaving out those registered already, with what they nest, and those of
        the same uid as their target.

        Raises
        ------
        ValueError
            If the target is not of the same structure, naming the path of
            tags to where it differs.
        """
        if type(source) is not type(target):
            raise ValueError(
                f"Cannot register {path} as unchanged: it is a "
                f"{type(source).__name__} in the source and a "
                f"{type(target).__name__} in the target."
            )
        if source.uid in self._migrators:
            return []
        pairs = [] if source.uid == target.uid else [(source, target)]
        for nested, nested_target, nested_path in self._nested_pairs(
            source, target, path
        ):
            pairs.extend(self._pair_unchanged(nested, nested_target, nested_path))
        return pairs

    @staticmethod
    def _nested_pairs(
        source: AttributeSchema, target: AttributeSchema, path: str
    ) -> list[tuple[AttributeSchema, AttributeSchema, str]]:
        """Pair the attribute schemas that a source and a target attribute
        schema of the same kind nest, each with its path.

        Raises
        ------
        ValueError
            If an object of the target has no attribute of a tag, or a union
            of the target has another number of members.
        """
        if isinstance(source, ObjectAttributeSchema):
            attributes = cast(ObjectAttributeSchema, target).attributes
            missing = [tag for tag in source.attributes if tag not in attributes]
            if missing:
                raise ValueError(
                    f"Cannot register {path} as unchanged: the target has no "
                    f"attribute {missing[0]!r}."
                )
            return [
                (nested, attributes[tag], f"{path}.{tag}")
                for tag, nested in source.attributes.items()
            ]
        if isinstance(source, ListAttributeSchema):
            item = cast(ListAttributeSchema, target).attribute
            return [(source.attribute, item, f"{path}.{source.attribute.tag}")]
        if isinstance(source, UnionAttributeSchema):
            members = cast(UnionAttributeSchema, target).attributes
            if len(source.attributes) != len(members):
                raise ValueError(
                    f"Cannot register {path} as unchanged: the union has "
                    f"{len(source.attributes)} members in the source and "
                    f"{len(members)} in the target."
                )
            return [
                (member, target_member, f"{path}.{member.tag}")
                for member, target_member in zip(
                    source.attributes, members, strict=True
                )
            ]
        return []


class UnchangedAttributeMigrator(AttributeMigrator):
    """Moves an attribute to a target attribute schema that holds the same
    values, at any depth.

    What an attribute holds is kept: its three values, what it was left to map,
    what was refused of it, how it is shown, and its mapping item. What refers
    to a schema is moved: the schema uid of the attribute, and of every
    attribute nested in its values. A nested attribute is moved to the
    attribute of the same tag in an object, to the attribute of a list, and to
    the member of the same value type in a union.

    Created with a registry, a nested attribute whose schema is registered is
    instead migrated by its registered migrator to its registered target, and
    what that loses of the value in effect is reported.
    """

    def __init__(self, attribute_migrators: AttributeMigrators | None = None):
        """Create the migrator.

        Parameters
        ----------
        attribute_migrators: AttributeMigrators | None = None
            The registry of the migrators of nested attributes, or None to move
            every nested attribute as it is.
        """
        self._attribute_migrators = attribute_migrators

    def migrate(
        self, attribute: AnyAttribute, target: AttributeSchema
    ) -> MigratedAttribute:
        """Move an attribute to the target schema.

        Parameters
        ----------
        attribute: AnyAttribute
            The attribute to move. Not changed.
        target: AttributeSchema
            The attribute schema of the target root to move it to.

        Returns
        -------
        MigratedAttribute
            The attribute on the target schema, with what it nests moved to the
            nested schemas of the target or migrated by its registered
            migrator, and what that lost of the value in effect.

        Raises
        ------
        ValueError
            If the target, or a schema it nests, is of another value type, as
            the values of the attribute could not be held by it.
        """
        if attribute.attribute_value_type != self._value_type(target):
            raise ValueError(
                f"Cannot move attribute {attribute.uid} of value type "
                f"{attribute.attribute_value_type.name} to schema {target.uid} of "
                f"value type {self._value_type(target).name}."
            )
        return self._migrate_values(
            attribute, target, partial(self._move_value, target=target)
        )

    def _move_value(
        self, value: Any, target: AttributeSchema
    ) -> tuple[Any, Sequence[str]]:
        """Move what a value of an attribute nests to the nested schemas of the
        target, and tell what it lost."""
        if isinstance(target, ObjectAttributeSchema) and isinstance(value, Mapping):
            moved = {
                tag: self._move_nested(
                    nested, partial(self._nested_of_object, target, tag)
                )
                for tag, nested in value.items()
            }
            return (
                {tag: result.attribute for tag, result in moved.items()},
                [lost for result in moved.values() for lost in result.lost],
            )
        if isinstance(target, ListAttributeSchema) and isinstance(value, Sequence):
            results = [
                self._move_nested(nested, lambda: target.attribute) for nested in value
            ]
            return (
                [result.attribute for result in results],
                [lost for result in results for lost in result.lost],
            )
        if isinstance(target, UnionAttributeSchema):
            result = self._move_nested(
                value, partial(self._member_of_union, target, value)
            )
            return result.attribute, result.lost
        return value, ()

    def _move_nested(
        self, nested: AnyAttribute, find_target: Callable[[], AttributeSchema]
    ) -> MigratedAttribute:
        """Migrate a nested attribute by the migrator registered for its schema
        to its registered target, else move it to the target found."""
        registered = (
            None
            if self._attribute_migrators is None
            else self._attribute_migrators.get(nested.schema_uid)
        )
        if registered is not None:
            migrator, target = registered
            return migrator.migrate(nested, target)
        return self.migrate(nested, find_target())

    @staticmethod
    def _nested_of_object(target: ObjectAttributeSchema, tag: str) -> AttributeSchema:
        """Return the attribute schema of a tag in an object attribute schema.

        Raises
        ------
        ValueError
            If the object attribute schema has no attribute of the tag.
        """
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
        """Return the member a union's value is moved to: the one of its own
        schema where the target has it, else the first of its value type.

        Raises
        ------
        ValueError
            If the union has no member of the value type of the value.
        """
        members = [
            member
            for member in target.attributes
            if UnchangedAttributeMigrator._value_type(member)
            == value.attribute_value_type
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
        """Return the value type of a schema, which every concrete schema
        declares."""
        return cast(AnyAttributeSchema, schema).attribute_value_type
