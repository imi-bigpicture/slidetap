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

"""Running the migration of a project without saving it, and working out what
the curator has to resolve."""

import contextlib
import dataclasses
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from uuid import UUID

from slidetap.database import (
    DatabaseAttributeMigrationIssue,
    DatabaseMigrationObject,
)
from slidetap.external_interfaces import SchemaMigration
from slidetap.model import (
    AnnotationSchema,
    AnyAttribute,
    AttributeSchema,
    Dataset,
    DatasetSchema,
    ImageSchema,
    Item,
    ItemSchema,
    MetadataSearchItem,
    MigrationError,
    ObjectMigrationResult,
    ObservationSchema,
    Project,
    ProjectSchema,
    RootSchemaIndex,
    SampleSchema,
    UnresolvedAttributeMigration,
)
from slidetap.services.validators.attribute_validator import AttributeValidator

AnyObjectSchema = ProjectSchema | DatasetSchema | ItemSchema
"""The schema of what a migration is given: a project, a dataset, or an item."""


@dataclass(frozen=True)
class ObjectInMigration:
    """An object of the project, and what the migration returned for it."""

    source: Project | Dataset | Item
    """The object as it is on the source root."""

    target_schema: AnyObjectSchema
    """Its schema on the target root."""

    target_attributes: Mapping[str, AnyAttribute | UnresolvedAttributeMigration]
    """Its attributes on the target schema by tag, each migrated, or
    unresolved for the curator to resolve."""

    target_private_attributes: Mapping[str, AnyAttribute | UnresolvedAttributeMigration]
    """Its private attributes on the target schema, as `target_attributes`."""

    @property
    def identifier(self) -> str:
        """The name of the project or dataset, or the identifier of the item."""
        if isinstance(self.source, Item):
            return self.source.identifier
        return self.source.name

    @property
    def order(self) -> tuple[int, str]:
        """Where the object goes among those of a migration: the project, the
        dataset, then the items by identifier."""
        if isinstance(self.source, Project):
            return 0, self.identifier
        if isinstance(self.source, Dataset):
            return 1, self.identifier
        return 2, self.identifier

    def unresolved(
        self,
    ) -> Iterator[tuple[str, UnresolvedAttributeMigration, AttributeSchema | None]]:
        """Iterate the unresolved attributes, public then private.

        Returns
        -------
        Iterator[tuple[str, UnresolvedAttributeMigration, AttributeSchema | None]]
            The tag and the unresolved attribute, with the attribute schema of
            the tag among the public or the private attributes of the target
            schema, as the attribute is, or None where it has none.
        """
        for attributes, schemas in (
            (self.target_attributes, self.target_schema.attributes),
            (self.target_private_attributes, self.target_schema.private_attributes),
        ):
            for tag, attribute in attributes.items():
                if isinstance(attribute, UnresolvedAttributeMigration):
                    yield tag, attribute, schemas.get(tag)


@dataclass(frozen=True)
class SearchItemInMigration:
    """A search item of the project, and the item schema the migration moves it
    to."""

    source: MetadataSearchItem
    """The search item as it is on the source root."""

    target_schema: ItemSchema
    """Its item schema on the target root."""


class ProjectMigrationPlanner:
    """Runs the migration of a root on the objects and search items of a
    project without saving anything, checks what it returns against the target
    root, and works out the attribute issues the curator resolves.

    An attribute issue is an attribute the migration left unresolved, a
    top-level attribute that was valid before and that the migration left
    invalid, or an attribute with a value that the migration dropped.
    """

    ITEM_SCHEMA_KINDS = (SampleSchema, ImageSchema, AnnotationSchema, ObservationSchema)

    def __init__(
        self,
        source_root: RootSchemaIndex,
        target_root: RootSchemaIndex,
        migration: SchemaMigration,
    ):
        """Create the planner of a migration.

        Parameters
        ----------
        source_root: RootSchemaIndex
            The root the project is on.
        target_root: RootSchemaIndex
            The root the project is migrated to.
        migration: SchemaMigration
            The migration of the source root.
        """
        self._source_root = source_root
        self._target_root = target_root
        self._migration = migration

    def migrate_objects(
        self, sources: Iterable[Project | Dataset | Item]
    ) -> list[ObjectInMigration]:
        """Run the migration for objects of the project, on copies of them, and
        check what it returns against the target root.

        Parameters
        ----------
        sources: Iterable[Project | Dataset | Item]
            The project, the dataset, and the items, on the source root.

        Returns
        -------
        list[ObjectInMigration]
            The objects, with every attribute that the migration left invalid,
            and that was valid before, unresolved.

        Raises
        ------
        MigrationError
            If the migration returns what it may not.
        """
        return [
            self._check_against_target_schema(
                self._pair_with_target_schema(source, self._migrate_object_copy(source))
            )
            for source in sources
        ]

    def migrate_search_items(
        self, search_items: Iterable[MetadataSearchItem]
    ) -> list[SearchItemInMigration]:
        """Pair search items of the project with the item schemas the migration
        moves them to.

        Parameters
        ----------
        search_items: Iterable[MetadataSearchItem]
            The search items, on the source root.

        Returns
        -------
        list[SearchItemInMigration]
            The search items, with their target item schemas.

        Raises
        ------
        MigrationError
            If an item schema is migrated off the item schemas of its kind in
            the target root.
        """
        return [
            SearchItemInMigration(
                search_item,
                self._get_target_item_schema(
                    f"search item {search_item.uid}",
                    search_item.schema_uid,
                    self._migration.migrate_item_schema(
                        self._source_root.get_item(search_item.schema_uid)
                    ).uid,
                ),
            )
            for search_item in search_items
        ]

    def create_attribute_issues(
        self, object_: ObjectInMigration
    ) -> Iterable[DatabaseAttributeMigrationIssue]:
        """Make the attribute issues of what an object left unresolved, and of
        what it dropped.

        Parameters
        ----------
        object_: ObjectInMigration
            The object, checked.

        Returns
        -------
        Iterable[DatabaseAttributeMigrationIssue]
            An attribute issue for each unresolved attribute and each dropped
            attribute, with the original given its display value.

        Raises
        ------
        MigrationError
            If an unresolved attribute is not a tag of the target schema.
        """
        for tag, unresolved, schema in object_.unresolved():
            original = None
            if unresolved.original is not None:
                original = unresolved.original.model_copy(deep=True)
                self._set_display_value(original)
            if schema is None:
                raise MigrationError(
                    f"The migration left {tag!r} of {object_.source.uid} "
                    f"unresolved, which is not an attribute of the target schema."
                )
            yield DatabaseAttributeMigrationIssue(
                original.schema_uid if original is not None else None,
                schema.uid,
                original,
                unresolved.proposed,
                unresolved.problem,
            )
        for attribute in self.get_dropped_attributes(object_):
            original = attribute.model_copy(deep=True)
            self._set_display_value(original)
            schema = self._get_source_attribute_schema(original.schema_uid)
            display_name = (
                schema.display_name if schema is not None else str(original.schema_uid)
            )
            value = original.display_value
            dropped = display_name if value is None else f"'{value}' of {display_name}"
            yield DatabaseAttributeMigrationIssue(
                original.schema_uid,
                None,
                original,
                None,
                f"{dropped} is dropped: it has no place in "
                f"{self._target_root.display_name}.",
            )

    def refuse_changed_plan(
        self,
        project_name: str,
        objects: Iterable[ObjectInMigration],
        planned_unresolved: Iterable[tuple[UUID, str]],
        planned_dropped: Iterable[tuple[UUID, UUID | None]],
    ) -> None:
        """Refuse a migration that no longer leaves unresolved or drops what
        the plan has attribute issues of.

        Parameters
        ----------
        project_name: str
            The name of the project, for the error.
        objects: Iterable[ObjectInMigration]
            The objects of the project, as the migration returned them now.
        planned_unresolved: Iterable[tuple[UUID, str]]
            The uid of the object and the target tag of each attribute issue
            of the plan with a target.
        planned_dropped: Iterable[tuple[UUID, UUID | None]]
            The uid of the object and the source attribute schema uid of each
            dropped attribute of the plan.

        Raises
        ------
        MigrationError
            If the attributes left unresolved or dropped are not those of the
            plan.
        """
        objects = list(objects)
        now: set[tuple[UUID, str | UUID | None]] = {
            (object_.source.uid, tag)
            for object_ in objects
            for tag, _, _ in object_.unresolved()
        }
        now.update(
            (object_.source.uid, attribute.schema_uid)
            for object_ in objects
            for attribute in self.get_dropped_attributes(object_)
        )
        planned: set[tuple[UUID, str | UUID | None]] = {
            *planned_unresolved,
            *planned_dropped,
        }
        if now != planned:
            raise MigrationError(
                f"The migration of project {project_name} no longer leaves "
                f"unresolved or drops what was planned: {len(now - planned)} "
                f"attributes are unresolved or dropped that are not in the plan, "
                f"and {len(planned - now)} in the plan are no longer. Revert "
                f"the migration and start it again."
            )

    @classmethod
    def get_dropped_attributes(cls, object_: ObjectInMigration) -> list[AnyAttribute]:
        """Get the dropped attributes of an object: those with a value that the
        migration neither converted nor left unresolved.

        Parameters
        ----------
        object_: ObjectInMigration
            The object, checked.

        Returns
        -------
        list[AnyAttribute]
            The dropped attributes of the source object.
        """
        kept = {
            attribute.uid
            for attribute in (
                *cls.get_migrated_attributes(object_.target_attributes).values(),
                *cls.get_migrated_attributes(
                    object_.target_private_attributes
                ).values(),
                *(
                    unresolved.original
                    for _, unresolved, _ in object_.unresolved()
                    if unresolved.original is not None
                ),
            )
        }
        return [
            attribute
            for attribute in (
                *object_.source.attributes.values(),
                *object_.source.private_attributes.values(),
            )
            if attribute.uid not in kept and attribute.value is not None
        ]

    @staticmethod
    def get_migrated_attributes(
        attributes: Mapping[str, AnyAttribute | UnresolvedAttributeMigration],
    ) -> dict[str, AnyAttribute]:
        """Get the migrated attributes of a mapping, leaving out the unresolved.

        Parameters
        ----------
        attributes: Mapping[str, AnyAttribute | UnresolvedAttributeMigration]
            The attributes of an object on the target schema, by tag.

        Returns
        -------
        dict[str, AnyAttribute]
            The migrated attributes, by tag.
        """
        return {
            tag: attribute
            for tag, attribute in attributes.items()
            if not isinstance(attribute, UnresolvedAttributeMigration)
        }

    @classmethod
    def get_issue_attribute_schema(
        cls,
        target_root: RootSchemaIndex,
        object_: DatabaseMigrationObject,
        issue: DatabaseAttributeMigrationIssue,
    ) -> tuple[str, AttributeSchema]:
        """Get the target tag and attribute schema of an attribute issue.

        Parameters
        ----------
        target_root: RootSchemaIndex
            The root the migration is to.
        object_: DatabaseMigrationObject
            The object of the migration the attribute issue is of.
        issue: DatabaseAttributeMigrationIssue
            An attribute issue of the object with a target.

        Returns
        -------
        tuple[str, AttributeSchema]
            The tag and attribute schema in the target schema of the object, a
            public or else a private attribute.

        Raises
        ------
        MigrationError
            If the target schema has no attribute of the attribute schema of
            the attribute issue, or it has none.
        """
        target_schema = cls._get_object_schema(
            target_root, object_.target_object_schema_uid
        )
        for tag, attribute_schema in (
            *target_schema.attributes.items(),
            *target_schema.private_attributes.items(),
        ):
            if attribute_schema.uid == issue.target_attribute_schema_uid:
                return tag, attribute_schema
        raise MigrationError(
            f"Attribute issue {issue.uid} is of attribute schema "
            f"{issue.target_attribute_schema_uid}, which is not an attribute of schema "
            f"{target_schema.uid}."
        )

    @staticmethod
    def refuse_attribute_off_schema(
        object_uid: UUID,
        tag: str,
        attribute: AnyAttribute,
        schema: AttributeSchema | None,
    ) -> AttributeSchema:
        """Refuse an attribute that is not on the attribute schema of its tag.

        Parameters
        ----------
        object_uid: UUID
            The uid of the object of the attribute, for the error.
        tag: str
            The target tag of the attribute.
        attribute: AnyAttribute
            The attribute.
        schema: AttributeSchema | None
            The attribute schema of the tag in the target schema, or None
            where it has none.

        Returns
        -------
        AttributeSchema
            The attribute schema of the tag.

        Raises
        ------
        MigrationError
            If the target schema has no attribute of the tag, or the attribute
            is on another attribute schema.
        """
        if schema is None or schema.uid != attribute.schema_uid:
            raise MigrationError(
                f"Attribute {attribute.uid} of {object_uid} is migrated to "
                f"schema {attribute.schema_uid} as {tag!r}, which is not an "
                f"attribute of the target schema."
            )
        return schema

    def _migrate_object_copy(
        self, source: Project | Dataset | Item
    ) -> ObjectMigrationResult:
        """Run the migration for an object, on a copy of it.

        Parameters
        ----------
        source: Project | Dataset | Item
            The object, on the source root.

        Returns
        -------
        ObjectMigrationResult
            What the migration returned for the object.
        """
        copy = source.model_copy(deep=True)
        if isinstance(copy, Project):
            return self._migration.migrate_project(copy)
        if isinstance(copy, Dataset):
            return self._migration.migrate_dataset(copy)
        return self._migration.migrate_item(copy)

    def _pair_with_target_schema(
        self, source: Project | Dataset | Item, migrated: ObjectMigrationResult
    ) -> ObjectInMigration:
        """Pair an object with what the migration returned for it, on the
        target schema the migration put it on.

        Parameters
        ----------
        source: Project | Dataset | Item
            The object, on the source root.
        migrated: ObjectMigrationResult
            What the migration returned for the object.

        Returns
        -------
        ObjectInMigration
            The object, with the target schema and what the migration returned.

        Raises
        ------
        MigrationError
            If the target schema is not the project or the dataset schema of
            the target root for the project or the dataset, or not an item
            schema of the target root of the same kind for an item.
        """
        if isinstance(source, Project | Dataset):
            target_schema: AnyObjectSchema = (
                self._target_root.project
                if isinstance(source, Project)
                else self._target_root.dataset
            )
            if migrated.schema_uid != target_schema.uid:
                raise MigrationError(
                    f"The migration put {source.uid} on schema "
                    f"{migrated.schema_uid}, not on {target_schema.uid} of the "
                    f"target root."
                )
        else:
            target_schema = self._get_target_item_schema(
                f"item {source.uid}", source.schema_uid, migrated.schema_uid
            )
        return ObjectInMigration(
            source,
            target_schema,
            migrated.attributes,
            migrated.private_attributes,
        )

    def _get_target_item_schema(
        self, name: str, source_schema_uid: UUID, target_schema_uid: UUID
    ) -> ItemSchema:
        """Get the item schema of the target root an item or a search item is
        migrated to, which must be of the kind of its source schema.

        Parameters
        ----------
        name: str
            What it is, for the error.
        source_schema_uid: UUID
            The uid of its source schema.
        target_schema_uid: UUID
            The uid of the target schema the migration put it on.

        Returns
        -------
        ItemSchema
            The target schema.

        Raises
        ------
        MigrationError
            If the target root has no item schema of the uid, or one of
            another kind.
        """
        source_schema = self._source_root.items.get(source_schema_uid)
        target_schema = self._target_root.items.get(target_schema_uid)
        if target_schema is None or not any(
            isinstance(source_schema, kind) and isinstance(target_schema, kind)
            for kind in self.ITEM_SCHEMA_KINDS
        ):
            raise MigrationError(
                f"The migration put {name} on schema {target_schema_uid}, which "
                f"is not an item schema of the same kind in the target root."
            )
        return target_schema

    def _check_against_target_schema(
        self, object_: ObjectInMigration
    ) -> ObjectInMigration:
        """Refuse what the migration returned off the target schema, and leave
        unresolved what it left invalid that was valid.

        Parameters
        ----------
        object_: ObjectInMigration
            The object, as the migration returned it.

        Returns
        -------
        ObjectInMigration
            The object, with every attribute that the migration left invalid,
            and that was valid before, unresolved.

        Raises
        ------
        MigrationError
            If an attribute is not the target schema's by tag, or an unresolved
            attribute is not a tag of the target schema, among the public or
            the private attributes as it is, or is proposed on another
            attribute schema.
        """
        uid, target_schema = object_.source.uid, object_.target_schema
        for attributes, schemas in (
            (object_.target_attributes, target_schema.attributes),
            (object_.target_private_attributes, target_schema.private_attributes),
        ):
            for tag, attribute in attributes.items():
                if isinstance(attribute, UnresolvedAttributeMigration):
                    continue
                self.refuse_attribute_off_schema(uid, tag, attribute, schemas.get(tag))
        for tag, unresolved, attribute_schema in object_.unresolved():
            if attribute_schema is None:
                raise MigrationError(
                    f"The migration left {tag!r} of {uid} unresolved, which "
                    f"is not an attribute of the target schema."
                )
            if unresolved.proposed is not None:
                self.refuse_attribute_off_schema(
                    uid, tag, unresolved.proposed, attribute_schema
                )
        return self._unresolve_invalidated_attributes(object_)

    def _unresolve_invalidated_attributes(
        self, object_: ObjectInMigration
    ) -> ObjectInMigration:
        """Leave unresolved every top-level attribute that the migration left
        invalid, and that was valid before: one newly required and without a
        value, or one whose value is not valid on the target schema. One that
        was invalid before is left as it is.

        Parameters
        ----------
        object_: ObjectInMigration
            The object, as the migration returned it.

        Returns
        -------
        ObjectInMigration
            The object, with those attributes unresolved.
        """
        source_schema = self._get_object_schema(
            self._source_root, object_.source.schema_uid
        )
        attributes = dict(object_.target_attributes)
        for tag, target_attribute_schema in object_.target_schema.attributes.items():
            attribute = attributes.get(tag)
            if isinstance(attribute, UnresolvedAttributeMigration):
                continue
            if self._is_attribute_valid(attribute, target_attribute_schema):
                continue
            source_tag, original = self._get_original_attribute(
                object_.source, attribute, tag
            )
            source_attribute_schema = source_schema.attributes.get(source_tag)
            if source_attribute_schema is not None and not self._is_attribute_valid(
                original, source_attribute_schema
            ):
                continue
            attributes[tag] = UnresolvedAttributeMigration(
                original=original,
                proposed=attribute,
                problem=(
                    f"Required in {self._target_root.display_name}, has no value."
                    if attribute is None or attribute.value is None
                    else f"Not a valid value in {self._target_root.display_name}."
                ),
            )
        return dataclasses.replace(object_, target_attributes=attributes)

    @staticmethod
    def _get_original_attribute(
        source: Project | Dataset | Item, attribute: AnyAttribute | None, tag: str
    ) -> tuple[str, AnyAttribute | None]:
        """Get the attribute of the source object a migrated attribute was.

        Parameters
        ----------
        source: Project | Dataset | Item
            The object, on the source root.
        attribute: AnyAttribute | None
            The migrated attribute, or None where there is none.
        tag: str
            The target tag of the migrated attribute.

        Returns
        -------
        tuple[str, AnyAttribute | None]
            The source tag and the attribute of the same uid, else the tag and
            the attribute of the source object at it, None where it has none.
        """
        if attribute is not None:
            for source_tag, original in source.attributes.items():
                if original.uid == attribute.uid:
                    return source_tag, original
        return tag, source.attributes.get(tag)

    @staticmethod
    def _is_attribute_valid(
        attribute: AnyAttribute | None, schema: AttributeSchema
    ) -> bool:
        """Check if an attribute is valid on an attribute schema.

        Parameters
        ----------
        attribute: AnyAttribute | None
            The attribute, or None where there is none.
        schema: AttributeSchema
            The attribute schema.

        Returns
        -------
        bool
            Whether the attribute is valid, or None is, as the schema is
            optional.
        """
        if attribute is None:
            return schema.optional
        return AttributeValidator.validate_attribute(
            attribute.model_copy(deep=True), schema
        )

    @staticmethod
    def _get_object_schema(root: RootSchemaIndex, schema_uid: UUID) -> AnyObjectSchema:
        """Get the project, dataset, or item schema of a uid in a root.

        Parameters
        ----------
        root: RootSchemaIndex
            The source or target root.
        schema_uid: UUID
            The uid of the schema.

        Returns
        -------
        AnyObjectSchema
            The schema.

        Raises
        ------
        KeyError
            If the root has no object schema of the uid.
        """
        if schema_uid == root.project.uid:
            return root.project
        if schema_uid == root.dataset.uid:
            return root.dataset
        return root.items[schema_uid]

    def _get_source_attribute_schema(
        self, attribute_schema_uid: UUID
    ) -> AttributeSchema | None:
        """Get an attribute schema of the source root, public or private.

        Parameters
        ----------
        attribute_schema_uid: UUID
            The uid of the attribute schema.

        Returns
        -------
        AttributeSchema | None
            The attribute schema, or None where the source root has none of
            the uid.
        """
        return self._source_root.attributes.get(
            attribute_schema_uid
        ) or self._source_root.private_attributes.get(attribute_schema_uid)

    def _set_display_value(self, attribute: AnyAttribute) -> None:
        """Set the display value of an attribute of the source root, where its
        schema is known.

        Parameters
        ----------
        attribute: AnyAttribute
            The attribute, given its display value.
        """
        schema = self._get_source_attribute_schema(attribute.schema_uid)
        if schema is None:
            return
        if attribute.value is None:
            attribute.display_value = None
            return
        with contextlib.suppress(KeyError, ValueError):
            attribute.display_value = schema.create_display_value(attribute.value)
