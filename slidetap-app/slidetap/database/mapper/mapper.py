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

"""Mapper specific to a attribute schema containing mapping items."""

import re
from typing import Generic, Iterable, List, Optional, Sequence
from uuid import UUID, uuid4

from slidetap.database.attribute import DatabaseAttribute
from slidetap.database.db import DbBase, db
from slidetap.database.mapper.mapping import MappingItem
from slidetap.model.attribute import Attribute, AttributeType
from sqlalchemy import Uuid, select
from sqlalchemy.orm import Mapped


class Mapper(DbBase, Generic[AttributeType]):
    uid: Mapped[UUID] = db.Column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = db.Column(db.String(128), index=True, unique=True)

    attribute_schema_uid = db.Column(Uuid, default=uuid4, index=True)
    mappings: Mapped[List[MappingItem[AttributeType]]] = db.relationship(
        MappingItem,
        single_parent=True,
        foreign_keys=MappingItem.mapper_uid,
        cascade="all, delete-orphan",
    )  # type: ignore

    root_attribute_schema_uid: Mapped[UUID] = db.Column(Uuid, index=True)

    def __init__(
        self,
        name: str,
        attribute_schema_uid: UUID,
        root_attribute_schema_uid: UUID,
        mappings: Optional[Iterable[MappingItem[AttributeType]]] = None,
        add: bool = True,
        commit: bool = True,
    ):
        if mappings is None:
            mappings = []
        super().__init__(
            name=name,
            attribute_schema_uid=attribute_schema_uid,
            root_attribute_schema_uid=root_attribute_schema_uid,
            mappings=mappings,
            add=add,
            commit=commit,
        )

    @property
    def expressions(self) -> Iterable[str]:
        return db.session.scalars(
            select(MappingItem.expression)
            .where(MappingItem.mapper_uid == self.uid)
            .order_by(MappingItem.hits.desc())
        )

    def get_mapping(self, expression: str) -> MappingItem[AttributeType]:
        return db.session.scalars(
            select(MappingItem).filter_by(mapper_uid=self.uid, expression=expression)
        ).one()

    def get_optional_mapping(
        self, expression: str
    ) -> Optional[MappingItem[AttributeType]]:
        return db.session.scalars(
            select(MappingItem).filter_by(mapper_uid=self.uid, expression=expression)
        ).one_or_none()

    def add(
        self, expression: str, attribute: Attribute[AttributeType], commit: bool = True
    ) -> MappingItem:
        mapping = self.get_optional_mapping(expression)
        if mapping is not None:
            mapping.attribute = attribute
            return mapping
        mapping = MappingItem[AttributeType](expression, attribute)
        self.mappings.append(mapping)
        if commit:
            db.session.commit()
        return mapping

    def add_multiple(
        self,
        expressions: Sequence[str],
        value: Attribute[AttributeType],
        commit: bool = True,
    ) -> List[MappingItem]:
        mappings = [self.add(expression, value, False) for expression in expressions]
        if commit:
            db.session.commit()
        return mappings

    def get_mapping_for_value(
        self, mappable_value: str
    ) -> Optional[MappingItem[AttributeType]]:
        if mappable_value is None:
            return None
        for expression in self.expressions:
            if re.match(expression, mappable_value) is not None:
                return self.get_mapping(expression)
        return None

    def delete(self) -> None:
        db.session.delete(self)
        db.session.commit()

    def update_name(self, name: str) -> None:
        self.name = name
        db.session.commit()

    @classmethod
    def get(cls, mapper_uid: UUID) -> "Mapper":
        mapper = db.session.get(cls, mapper_uid)
        if mapper is None:
            raise ValueError(f"Mapper with uid {mapper_uid} does not exist")
        return mapper

    @classmethod
    def get_by_name(cls, name: str) -> Optional["Mapper"]:
        return db.session.scalars(select(cls).filter_by(name=name)).one_or_none()

    @classmethod
    def get_all(cls) -> Iterable["Mapper"]:
        return db.session.scalars(select(Mapper))

    @classmethod
    def get_for_attribute(cls, attribute: Attribute) -> Iterable["Mapper"]:
        return db.session.scalars(
            select(Mapper).where(cls.attribute_schema_uid == attribute.schema_uid)
        )

    @classmethod
    def get_for_root_attribute(cls, attribute: DatabaseAttribute) -> Iterable["Mapper"]:
        return db.session.scalars(
            select(Mapper).where(cls.root_attribute_schema_uid == attribute.schema_uid)
        )

    @classmethod
    def get_for_attribute_schema(cls, attribute_schema_uid: UUID) -> Iterable["Mapper"]:
        return db.session.scalars(
            select(Mapper).where(cls.root_attribute_schema_uid == attribute_schema_uid)
        )

    def get_mappable_attributes(self) -> Iterable[DatabaseAttribute]:
        """Return attributes that can be mapped by this mapper."""
        query = select(DatabaseAttribute).filter(
            DatabaseAttribute.schema_uid == self.root_attribute_schema_uid,
        )
        return db.session.scalars(query)
