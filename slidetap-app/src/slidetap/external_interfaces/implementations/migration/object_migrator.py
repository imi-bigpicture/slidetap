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

"""Migrating a project, a dataset, or an item to its schema on another root."""

from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from functools import cached_property
from typing import Any, Generic, TypeVar
from uuid import UUID

from slidetap.external_interfaces.implementations.migration.attribute_migrator import (
    AttributeMigrator,
    UnchangedAttributeMigrator,
)
from slidetap.model import (
    AnyAttribute,
    AttributeSchema,
    Dataset,
    DatasetSchema,
    EnumAttributeSchema,
    Item,
    ItemSchema,
    ListAttributeSchema,
    MigratedObject,
    ObjectAttributeSchema,
    Project,
    ProjectSchema,
    UnionAttributeSchema,
    UnresolvedAttribute,
)

ObjectSchema = ProjectSchema | DatasetSchema | ItemSchema
"""The schema of what is migrated: a project, a dataset, or an item."""

T = TypeVar("T", bound=Project | Dataset | Item)
DeclarationType = TypeVar("DeclarationType")


class MigrationKind(Enum):
    """What becomes of an attribute of the source root on the target root."""

    MOVED = "moved"
    """Moved as it is, to the attribute of the same place in the target."""

    MIGRATED = "migrated"
    """Migrated by the attribute migrator declared for it, with what it
    holds."""

    DROPPED = "dropped"
    """Left out, as the target has no place for it."""

    UNSET = "unset"
    """An attribute of the target that no source attribute becomes, declared
    unset or not."""

    UNDECLARED = "undeclared"
    """An attribute of the source that the migrator says nothing about, but
    cannot move as it is: one whose tag is not in the target, or whose target
    is of another kind or, for an enum, holds other values. A migrator with
    one is refused."""


@dataclass(frozen=True)
class AttributeMigration:
    """What becomes of an attribute, at one place in the object."""

    path: str
    """Where the attribute is: its tag, then `/tag` for an attribute of an
    object, `[]` for the attribute of a list, and `<index>` for a member of a
    union. `!` marks a private attribute."""

    kind: MigrationKind

    source: AttributeSchema | None
    """The attribute of the source root, None for one only in the target."""

    target: AttributeSchema | None
    """The attribute of the target root, None for one only in the source."""

    migrator: AttributeMigrator | None = None
    """The migrator of a migrated attribute."""


class ObjectMigrator(Generic[T]):
    """Migrates a project, a dataset, or an item from its schema in the source
    root to its schema in the target root.

    Every attribute whose tag is in both schemas is moved to the target
    attribute of that tag, at any depth, with the attributes it holds. What
    else becomes of an attribute is declared by its source or target attribute
    schema, at any depth: an attribute migrated by an attribute migrator, such
    as an enum whose values changed, one moved to another attribute of the same
    object, one dropped, and a target attribute left unset. A migrator is
    refused when it is created if a declaration is not of the schemas, or if it
    says nothing about a source attribute it cannot move as it is, see
    `MigrationKind.UNDECLARED`. A target attribute that no source attribute
    becomes is left without a value, declared unset or not.

    An attribute holding a value that loses it to an attribute migrator, as a
    value with no counterpart on the target, at any depth, is returned
    unresolved, under its target tag, with what could be migrated proposed.
    """

    def __init__(
        self,
        source: ObjectSchema,
        target: ObjectSchema,
        migrated: Sequence[tuple[AttributeSchema, AttributeMigrator]] = (),
        renamed: Sequence[tuple[AttributeSchema, AttributeSchema]] = (),
        dropped: Iterable[AttributeSchema] = (),
        unset: Iterable[AttributeSchema] = (),
    ):
        """Create a migrator between two schemas of the same kind.

        Parameters
        ----------
        source: ObjectSchema
            The project, dataset, or item schema of the source root.
        target: ObjectSchema
            The schema of the target root it becomes.
        migrated: Sequence[tuple[AttributeSchema, AttributeMigrator]] = ()
            Source attribute schemas whose values changed, with the migrator of
            their values.
        renamed: Sequence[tuple[AttributeSchema, AttributeSchema]] = ()
            Source attribute schemas, with the target attribute schema of another
            tag in the same object that each becomes.
        dropped: Iterable[AttributeSchema] = ()
            Source attribute schemas that are left out.
        unset: Iterable[AttributeSchema] = ()
            Target attribute schemas that no source attribute becomes, left
            without a value.

        Raises
        ------
        ValueError
            If an attribute schema is declared twice in a declaration, a
            declared attribute schema is not of the schema it is declared for,
            an attribute declared unset is one a source attribute becomes,
            or the migrator says nothing about a source attribute it cannot
            move as it is.
        """
        self._source = source
        self._target = target
        self._migrated = self._index("migrated", migrated, lambda pair: pair[0])
        self._renamed = self._index("renamed", renamed, lambda pair: pair[0])
        self._dropped = self._index("dropped", dropped, lambda schema: schema)
        self._unset = self._index("unset", unset, lambda schema: schema)
        self._unchanged = UnchangedAttributeMigrator()
        self._refuse_foreign()
        self._refuse_undeclared()
        self._refuse_set_unset()

    @property
    def source(self) -> ObjectSchema:
        return self._source

    @property
    def target(self) -> ObjectSchema:
        return self._target

    @property
    def migrated(self) -> tuple[tuple[AttributeSchema, AttributeMigrator], ...]:
        return tuple(self._migrated.values())

    @property
    def renamed(self) -> tuple[tuple[AttributeSchema, AttributeSchema], ...]:
        return tuple(self._renamed.values())

    @property
    def dropped(self) -> tuple[AttributeSchema, ...]:
        return tuple(self._dropped.values())

    @property
    def unset(self) -> tuple[AttributeSchema, ...]:
        return tuple(self._unset.values())

    def migrate(self, obj: T) -> MigratedObject:
        """The project, dataset, or item on the target schema."""
        unresolved: dict[str, UnresolvedAttribute] = {}
        attributes = self._migrate_attributes(
            obj.attributes,
            self._source.attributes,
            self._target.attributes,
            unresolved,
        )
        private_attributes = self._migrate_attributes(
            obj.private_attributes,
            self._source.private_attributes,
            self._target.private_attributes,
            unresolved,
        )
        return MigratedObject(
            schema_uid=self._target.uid,
            attributes=attributes,
            private_attributes=private_attributes,
            unresolved=unresolved,
        )

    def target_of(self, source: AttributeSchema) -> AttributeSchema | None:
        """The attribute schema of the target root that an attribute schema of
        the source root becomes, at any depth, or None where it is dropped or is
        not of the source schema."""
        found = self._targets.get(source.uid)
        if found is None:
            return None
        _, target = found
        return target

    def migrate_attribute(self, attribute: AnyAttribute) -> AnyAttribute | None:
        """An attribute of the source schema, at any depth, on the target
        schema, with the attributes it holds migrated, each of its values on its
        own, or None where its attribute schema has no target.

        Parameters
        ----------
        attribute: AnyAttribute
            The attribute to migrate, of the source schema. Not changed.
        """
        found = self._targets.get(attribute.schema_uid)
        if found is None:
            return None
        source, target = found
        return self._migrate(attribute, source, target, [])

    @cached_property
    def migrations(self) -> list[AttributeMigration]:
        """What becomes of every attribute of the two schemas, at any depth."""
        migrations: list[AttributeMigration] = []
        self._walk(self._source.attributes, self._target.attributes, "", migrations)
        self._walk(
            {
                f"!{tag}": schema
                for tag, schema in self._source.private_attributes.items()
            },
            {
                f"!{tag}": schema
                for tag, schema in self._target.private_attributes.items()
            },
            "",
            migrations,
        )
        return migrations

    @cached_property
    def _targets(self) -> dict[UUID, tuple[AttributeSchema, AttributeSchema]]:
        """The source and target attribute schema of every source attribute
        schema that has a target, at any depth, by the uid of the source."""
        targets: dict[UUID, tuple[AttributeSchema, AttributeSchema]] = {}
        for migration in self.migrations:
            if (
                migration.kind in (MigrationKind.MOVED, MigrationKind.MIGRATED)
                and migration.source is not None
                and migration.target is not None
            ):
                targets.setdefault(
                    migration.source.uid, (migration.source, migration.target)
                )
        return targets

    def _index(
        self,
        declaration: str,
        declared: Iterable[DeclarationType],
        schema_of: Callable[[DeclarationType], AttributeSchema],
    ) -> dict[UUID, DeclarationType]:
        """The declared, by the uid of the attribute schema each is of, refusing
        an attribute schema declared twice."""
        indexed: dict[UUID, DeclarationType] = {}
        twice: list[str] = []
        for entry in declared:
            schema = schema_of(entry)
            if schema.uid in indexed:
                twice.append(f"{schema.tag} ({schema.uid})")
            indexed[schema.uid] = entry
        if twice:
            raise ValueError(
                f"The migrator of {self._source.name} declares "
                f"{', '.join(twice)} as {declaration} more than once."
            )
        return indexed

    def _refuse_foreign(self) -> None:
        """Refuse declarations of attribute schemas that are not of the source
        or target schema they are declared for."""
        sources = self._attribute_schemas(self._source)
        targets = self._attribute_schemas(self._target)
        declarations: list[tuple[str, Iterable[AttributeSchema], set[UUID]]] = [
            ("migrated", (schema for schema, _ in self._migrated.values()), sources),
            ("renamed", (schema for schema, _ in self._renamed.values()), sources),
            ("renamed to", (schema for _, schema in self._renamed.values()), targets),
            ("dropped", self._dropped.values(), sources),
            ("unset", self._unset.values(), targets),
        ]
        foreign = [
            f"{schema.tag} ({schema.uid}) as {declaration}"
            for declaration, schemas, of in declarations
            for schema in schemas
            if schema.uid not in of
        ]
        if foreign:
            raise ValueError(
                f"The migrator of {self._source.name} declares "
                f"{', '.join(foreign)}, which are not attribute schemas of the "
                f"source or target schema they are declared for."
            )

    def _refuse_set_unset(self) -> None:
        """Refuse target attributes declared unset that a source attribute
        becomes."""
        unset = {
            migration.target.uid
            for migration in self.migrations
            if migration.kind == MigrationKind.UNSET and migration.target
        }
        set_unset = [
            f"{schema.tag} ({schema.uid})"
            for uid, schema in self._unset.items()
            if uid not in unset
        ]
        if set_unset:
            raise ValueError(
                f"The migrator of {self._source.name} declares "
                f"{', '.join(set_unset)} unset, which a source attribute becomes."
            )

    def _refuse_undeclared(self) -> None:
        undeclared = [
            migration.path
            for migration in self.migrations
            if migration.kind == MigrationKind.UNDECLARED
        ]
        if undeclared:
            raise ValueError(
                f"The migrator of {self._source.name} says nothing about "
                f"{', '.join(undeclared)}, which cannot be moved as it is to the "
                f"target schema."
            )

    def _migrate_attributes(
        self,
        attributes: Mapping[str, AnyAttribute],
        sources: Mapping[str, AttributeSchema],
        targets: Mapping[str, AttributeSchema],
        unresolved: dict[str, UnresolvedAttribute],
    ) -> dict[str, AnyAttribute]:
        """The attributes of an object schema by their tags in the target, with
        those that lost a value put in `unresolved` instead."""
        migrated: dict[str, AnyAttribute] = {}
        for target_tag, attribute, source, target in self._pairs(
            attributes, sources, targets
        ):
            reasons: list[str] = []
            migrated_attribute = self._migrate(attribute, source, target, reasons)
            if reasons:
                unresolved[target_tag] = UnresolvedAttribute(
                    original=attribute,
                    proposed=migrated_attribute,
                    reason=" ".join(dict.fromkeys(reasons)),
                )
            else:
                migrated[target_tag] = migrated_attribute
        return migrated

    def _pairs(
        self,
        attributes: Mapping[str, AnyAttribute],
        sources: Mapping[str, AttributeSchema],
        targets: Mapping[str, AttributeSchema],
    ) -> Iterator[tuple[str, AnyAttribute, AttributeSchema, AttributeSchema]]:
        """The attributes held by tag that are not dropped, with their target
        tag, source schema, and target schema."""
        for source_tag, attribute in attributes.items():
            source = sources.get(source_tag)
            if source is None:
                raise ValueError(
                    f"Attribute {attribute.uid} is held as {source_tag!r}, which is "
                    f"not an attribute of the source schema of {self._source.name}."
                )
            if source.uid in self._dropped:
                continue
            target_tag = self._target_key(source_tag, source, targets)
            if target_tag is None or target_tag not in targets:
                raise ValueError(
                    f"Attribute {attribute.uid} is held as {source_tag!r}, which "
                    f"has no target in the target schema of {self._target.name}."
                )
            yield target_tag, attribute, source, targets[target_tag]

    def _migrate(
        self,
        attribute: AnyAttribute,
        source: AttributeSchema,
        target: AttributeSchema,
        reasons: list[str],
    ) -> AnyAttribute:
        """The attribute on the target schema, with why the value in effect lost
        a value, at any depth, added to `reasons`."""
        declared = self._migrated.get(source.uid)
        if declared is not None:
            _, migrator = declared
            migrated = migrator.migrate(attribute, target)
            if attribute.value is not None and migrated.value is None:
                reasons.append(
                    f"'{attribute.value}' is no longer an option of "
                    f"{target.display_name}."
                )
            return migrated
        if not self._children(source):
            return self._unchanged.migrate(attribute, target)
        effective_layer = self._effective_layer(attribute)
        update: dict[str, Any] = {"schema_uid": target.uid}
        for layer in ("original_value", "updated_value", "mapped_value"):
            update[layer] = self._migrate_held(
                getattr(attribute, layer),
                source,
                target,
                reasons if layer == effective_layer else [],
            )
        return attribute.model_copy(update=update, deep=True)

    @staticmethod
    def _effective_layer(attribute: AnyAttribute) -> str | None:
        """The value of the attribute in effect: the original, updated, or
        mapped one, or None."""
        value = attribute.value
        if value is None:
            return None
        return next(
            layer
            for layer in ("updated_value", "mapped_value", "original_value")
            if getattr(attribute, layer) is value
        )

    def _migrate_held(
        self,
        value: Any,
        source: AttributeSchema,
        target: AttributeSchema,
        reasons: list[str],
    ) -> Any:
        """One value of an object, list, or union: the attributes it holds,
        migrated."""
        if value is None:
            return None
        if isinstance(source, ObjectAttributeSchema) and isinstance(
            target, ObjectAttributeSchema
        ):
            return {
                target_tag: self._migrate(nested, nested_source, nested_target, reasons)
                for target_tag, nested, nested_source, nested_target in self._pairs(
                    value, source.attributes, target.attributes
                )
            }
        if isinstance(source, ListAttributeSchema) and isinstance(
            target, ListAttributeSchema
        ):
            return [
                self._migrate(nested, source.attribute, target.attribute, reasons)
                for nested in value
            ]
        if isinstance(source, UnionAttributeSchema) and isinstance(
            target, UnionAttributeSchema
        ):
            return self._migrate_member(value, source, target, reasons)
        raise TypeError(f"Attribute schema {source.uid} holds no attributes.")

    def _migrate_member(
        self,
        attribute: AnyAttribute,
        source: UnionAttributeSchema,
        target: UnionAttributeSchema,
        reasons: list[str],
    ) -> AnyAttribute:
        """The member of a union, to the member of the same place in the
        target union."""
        for index, member in enumerate(source.attributes):
            if member.uid == attribute.schema_uid and index < len(target.attributes):
                return self._migrate(
                    attribute, member, target.attributes[index], reasons
                )
        raise ValueError(
            f"Attribute {attribute.uid} of schema {attribute.schema_uid} is not a "
            f"member of union {source.uid} with a member in union {target.uid}."
        )

    def _walk(
        self,
        sources: Mapping[str, AttributeSchema],
        targets: Mapping[str, AttributeSchema],
        path: str,
        migrations: list[AttributeMigration],
    ) -> None:
        """Pair the attributes of the two sides by key, and what they hold."""
        matched: set[str] = set()
        for key, source in sources.items():
            source_path = path + key
            if source.uid in self._dropped:
                self._walk_one_side(
                    source, source_path, MigrationKind.DROPPED, True, migrations
                )
                continue
            target_key = self._target_key(key, source, targets)
            target = None if target_key is None else targets.get(target_key)
            if target_key is None or target is None:
                self._walk_one_side(
                    source, source_path, MigrationKind.UNDECLARED, True, migrations
                )
                continue
            matched.add(target_key)
            declared = self._migrated.get(source.uid)
            if declared is not None:
                _, migrator = declared
                migrations.append(
                    AttributeMigration(
                        source_path, MigrationKind.MIGRATED, source, target, migrator
                    )
                )
                continue
            if self._differ(source, target):
                migrations.append(
                    AttributeMigration(
                        source_path, MigrationKind.UNDECLARED, source, target
                    )
                )
                continue
            migrations.append(
                AttributeMigration(source_path, MigrationKind.MOVED, source, target)
            )
            self._walk(
                self._children(source), self._children(target), source_path, migrations
            )
        for key, target in targets.items():
            if key in matched:
                continue
            # No source attribute becomes it, whether declared or not.
            self._walk_one_side(
                target, path + key, MigrationKind.UNSET, False, migrations
            )

    def _walk_one_side(
        self,
        schema: AttributeSchema,
        path: str,
        kind: MigrationKind,
        is_source: bool,
        migrations: list[AttributeMigration],
    ) -> None:
        """An attribute of one side only, and what it holds."""
        migrations.append(
            AttributeMigration(
                path,
                kind,
                schema if is_source else None,
                None if is_source else schema,
            )
        )
        for key, child in self._children(schema).items():
            self._walk_one_side(child, path + key, kind, is_source, migrations)

    def _target_key(
        self, key: str, source: AttributeSchema, targets: Mapping[str, AttributeSchema]
    ) -> str | None:
        """The key of the target attribute a source attribute becomes, among the
        attributes of the same object in the target, None if it is renamed to
        one that is not among them."""
        declared = self._renamed.get(source.uid)
        if declared is None:
            return key
        _, renamed_to = declared
        return next(
            (
                target_key
                for target_key, target in targets.items()
                if target.uid == renamed_to.uid
            ),
            None,
        )

    @classmethod
    def _attribute_schemas(cls, schema: ObjectSchema) -> set[UUID]:
        """The uids of the attribute schemas of an object schema, at any
        depth."""
        uids: set[UUID] = set()
        pending: list[AttributeSchema] = [
            *schema.attributes.values(),
            *schema.private_attributes.values(),
        ]
        while pending:
            attribute = pending.pop()
            uids.add(attribute.uid)
            pending.extend(cls._children(attribute).values())
        return uids

    @staticmethod
    def _differ(source: AttributeSchema, target: AttributeSchema) -> bool:
        """Whether an attribute of the source schema cannot be moved as it is to
        the target schema: one of another kind, or an enum of other values."""
        if type(source) is not type(target):
            return True
        return (
            isinstance(source, EnumAttributeSchema)
            and isinstance(target, EnumAttributeSchema)
            and set(source.allowed_values) != set(target.allowed_values)
        )

    @staticmethod
    def _children(schema: AttributeSchema) -> dict[str, AttributeSchema]:
        """What an attribute schema holds, by key."""
        if isinstance(schema, ObjectAttributeSchema):
            return {f"/{tag}": nested for tag, nested in schema.attributes.items()}
        if isinstance(schema, ListAttributeSchema):
            return {"[]": schema.attribute}
        if isinstance(schema, UnionAttributeSchema):
            return {
                f"<{index}>": member for index, member in enumerate(schema.attributes)
            }
        return {}
