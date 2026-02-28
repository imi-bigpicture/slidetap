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
from __future__ import annotations

from typing import Generic, Optional, Set
from uuid import UUID, uuid4

from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from slidetap.database.db import Base
from slidetap.database.types import attribute_db_type
from slidetap.model.attribute import Attribute, AttributeType
from slidetap.model.mapper import Mapper, MapperGroup, MappingItem


class DatabaseMapper(Base, Generic[AttributeType]):
    uid: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), index=True, unique=True)

    attribute_schema_uid: Mapped[UUID] = mapped_column(Uuid, index=True)
    root_attribute_schema_uid: Mapped[UUID] = mapped_column(Uuid, index=True)
    mapper_group_uid: Mapped[Optional[UUID]] = mapped_column(
        Uuid, ForeignKey("mapper_group.uid"), index=True, nullable=True
    )
    __table_args__ = (
        UniqueConstraint("attribute_schema_uid", "root_attribute_schema_uid"),
    )
    __tablename__ = "mapper"

    def __init__(
        self,
        name: str,
        attribute_schema_uid: UUID,
        root_attribute_schema_uid: UUID,
    ):
        super().__init__(
            uid=uuid4(),
            name=name,
            attribute_schema_uid=attribute_schema_uid,
            root_attribute_schema_uid=root_attribute_schema_uid,
        )

    @property
    def model(self):
        return Mapper(
            uid=self.uid,
            name=self.name,
            attribute_schema_uid=self.attribute_schema_uid,
            root_attribute_schema_uid=self.root_attribute_schema_uid,
        )


class DatabaseMappingItem(Base, Generic[AttributeType]):
    uid: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    mapper_uid: Mapped[UUID] = mapped_column(Uuid, ForeignKey("mapper.uid"), index=True)
    expression: Mapped[str] = mapped_column(String(128))
    attribute: Mapped[Attribute] = mapped_column(attribute_db_type)
    hits: Mapped[int] = mapped_column(Integer, default=0)

    mapper: Mapped[DatabaseMapper[AttributeType]] = relationship(
        DatabaseMapper,
        foreign_keys=mapper_uid,
    )

    __tablename__ = "mapping_item"

    def __init__(
        self,
        mapper_uid: UUID,
        expression: str,
        attribute: Attribute[AttributeType],
    ):
        super().__init__(
            uid=uuid4(),
            mapper_uid=mapper_uid,
            expression=expression,
            attribute=attribute,
            hits=0,
        )

    def update(self, expression: str, attribute: Attribute[AttributeType]):
        self.expression = expression
        self.attribute = attribute

    def increment_hits(self):
        self.hits += 1

    @property
    def model(self):
        return MappingItem(
            uid=self.uid,
            mapper_uid=self.mapper_uid,
            expression=self.expression,
            attribute=self.attribute,
            hits=self.hits,
        )


class DatabaseMapperGroup(Base):
    uid: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), index=True, unique=True)
    mappers: Mapped[Set[DatabaseMapper]] = relationship(
        "DatabaseMapper",
        foreign_keys="DatabaseMapper.mapper_group_uid",
    )  # type: ignore
    default_enabled: Mapped[bool] = mapped_column()

    __tablename__ = "mapper_group"

    def __init__(
        self,
        name: str,
        default_enabled: bool,
    ):
        super().__init__(uid=uuid4(), name=name, default_enabled=default_enabled)

    @property
    def model(self):
        return MapperGroup(
            uid=self.uid,
            name=self.name,
            mappers=[mapper.uid for mapper in self.mappers],
            default_enabled=self.default_enabled,
        )
