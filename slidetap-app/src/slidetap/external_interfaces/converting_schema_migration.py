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

"""A schema migration of object converters."""

from collections.abc import Iterable, Sequence
from functools import cached_property
from typing import Any
from uuid import UUID

from slidetap.external_interfaces.object_converter import (
    ConversionKind,
    ObjectConverter,
)
from slidetap.external_interfaces.schema_migration import (
    MigratedObject,
    SchemaMigration,
)
from slidetap.model import (
    AnyAttribute,
    AttributeSchema,
    Dataset,
    Item,
    ItemSchema,
    MetadataSearchItem,
    Project,
    RootSchema,
)


class ConvertingSchemaMigration(SchemaMigration):
    """Moves projects from a source root to a target root with an
    `ObjectConverter` for the project, the dataset, and each item schema of the
    source.

    A converter not given is a plain `ObjectConverter`, which declares nothing:
    for the project and the dataset, and for an item schema of the source that
    the target has under the same uid. An item schema of the source with
    neither a converter nor such a target is refused.

    `migrate_attribute` converts an attribute with the converter whose schemas
    hold it, at any depth, so that the mapping items of a mapper moved to the
    target root are converted as the attributes of the objects are.
    """

    def __init__(
        self,
        source: RootSchema,
        target: RootSchema,
        project_converter: ObjectConverter[Project] | None = None,
        dataset_converter: ObjectConverter[Dataset] | None = None,
        item_converters: Iterable[ObjectConverter[Item]] = (),
    ):
        """Create the migration between two roots.

        Parameters
        ----------
        source: RootSchema
            The root the projects are moved from.
        target: RootSchema
            The root the projects are moved to.
        project_converter: ObjectConverter[Project] | None = None
            The converter of the project.
        dataset_converter: ObjectConverter[Dataset] | None = None
            The converter of the dataset.
        item_converters: Iterable[ObjectConverter[Item]] = ()
            The converters of the items, each of its source item schema.

        Raises
        ------
        ValueError
            If an item schema of the source has neither a converter nor an item
            schema of the same uid in the target, a converter is given for an
            item schema that is not of the source or that already has one, or a
            plain converter created here says nothing about an attribute it
            cannot move as it is.
        """
        self._source = source
        self._target = target
        self._project_converter = (
            ObjectConverter[Project](source.project, target.project)
            if project_converter is None
            else project_converter
        )
        self._dataset_converter = (
            ObjectConverter[Dataset](source.dataset, target.dataset)
            if dataset_converter is None
            else dataset_converter
        )
        self._item_converters = self._create_item_converters(item_converters)

    @property
    def source(self) -> RootSchema:
        return self._source

    @property
    def target(self) -> RootSchema:
        return self._target

    @property
    def project_converter(self) -> ObjectConverter[Project]:
        return self._project_converter

    @property
    def dataset_converter(self) -> ObjectConverter[Dataset]:
        return self._dataset_converter

    @property
    def item_converters(self) -> Sequence[ObjectConverter[Item]]:
        """The converters of the items, one for each item schema of the
        source."""
        return list(self._item_converters.values())

    @property
    def converters(self) -> list[ObjectConverter[Any]]:
        """Every converter: of the project, the dataset, and the items."""
        return [
            self._project_converter,
            self._dataset_converter,
            *self._item_converters.values(),
        ]

    def migrate_project(self, project: Project) -> MigratedObject:
        return self._project_converter.migrate(project)

    def migrate_dataset(self, dataset: Dataset) -> MigratedObject:
        return self._dataset_converter.migrate(dataset)

    def migrate_item(self, item: Item) -> MigratedObject:
        return self._item_converter(f"Item {item.uid}", item.schema_uid).migrate(item)

    def migrate_search_item(self, search_item: MetadataSearchItem) -> UUID:
        """The target item schema of the converter of the item schema of the
        search item."""
        return self._item_converter(
            f"Search item {search_item.uid}", search_item.schema_uid
        ).target.uid

    def migrate_attribute(self, attribute: AnyAttribute) -> AnyAttribute | None:
        """The attribute converted by the converter whose schemas hold it, or
        None where it is dropped or not of the source root."""
        found = self._attributes.get(attribute.schema_uid)
        if found is None:
            return None
        converter, source, target = found
        return converter.convert_attribute(attribute, source, target)

    def _item_converter(self, name: str, schema_uid: UUID) -> ObjectConverter[Item]:
        """The converter of an item schema of the source root, for an item or a
        search item as named.

        Raises
        ------
        ValueError
            If the schema is not an item schema of the source root.
        """
        converter = self._item_converters.get(schema_uid)
        if converter is None:
            raise ValueError(
                f"{name} is of schema {schema_uid}, which is not an item schema of "
                f"root {self._source.name}."
            )
        return converter

    def _create_item_converters(
        self, declared: Iterable[ObjectConverter[Item]]
    ) -> dict[UUID, ObjectConverter[Item]]:
        """The declared converters, and a plain one for every other item schema
        of the source, to the item schema of the same uid in the target, by the
        uid of their source item schema."""
        source_items = self._item_schemas(self._source)
        target_items = self._item_schemas(self._target)
        by_source: dict[UUID, ObjectConverter[Item]] = {}
        for converter in declared:
            if converter.source.uid in by_source:
                raise ValueError(
                    f"Two converters are given for item schema "
                    f"{converter.source.name} ({converter.source.uid})."
                )
            by_source[converter.source.uid] = converter
        converters: dict[UUID, ObjectConverter[Item]] = {}
        for uid, source_item in source_items.items():
            converter = by_source.get(uid)
            if converter is not None:
                converters[uid] = converter
                continue
            target_item = target_items.get(uid)
            if target_item is None:
                raise ValueError(
                    f"Item schema {source_item.name} ({uid}) of root "
                    f"{self._source.name} has no converter, and no item schema of "
                    f"the same uid in root {self._target.name}."
                )
            converters[uid] = ObjectConverter[Item](source_item, target_item)
        unknown = by_source.keys() - source_items.keys()
        if unknown:
            raise ValueError(
                f"Converters are given for {', '.join(map(str, unknown))}, which "
                f"are not item schemas of root {self._source.name}."
            )
        return converters

    @staticmethod
    def _item_schemas(root: RootSchema) -> dict[UUID, ItemSchema]:
        return {
            **root.samples,
            **root.images,
            **root.observations,
            **root.annotations,
        }

    @cached_property
    def _attributes(
        self,
    ) -> dict[UUID, tuple[ObjectConverter[Any], AttributeSchema, AttributeSchema]]:
        """The converter, source, and target of every source attribute schema
        that has a target, at any depth."""
        attributes: dict[
            UUID, tuple[ObjectConverter[Any], AttributeSchema, AttributeSchema]
        ] = {}
        for converter in self.converters:
            for conversion in converter.conversions:
                if (
                    conversion.kind in (ConversionKind.MOVED, ConversionKind.CONVERTED)
                    and conversion.source is not None
                    and conversion.target is not None
                ):
                    attributes.setdefault(
                        conversion.source.uid,
                        (converter, conversion.source, conversion.target),
                    )
        return attributes
