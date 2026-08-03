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

import re
from typing import Generic
from uuid import UUID, uuid4

from sqlalchemy import (
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from slidetap.database.db import Base
from slidetap.database.types import attribute_db_type
from slidetap.model import (
    AnyAttribute,
    AttributeType,
    Mapper,
    MapperGroup,
    MappingItem,
)

# Table for mapping many-to-many mappers and mapper groups. A mapper can be
# used by several groups, for example a group per data source that share a
# mapper for a common attribute.
mapper_to_mapper_group = Table(
    "mapper_to_mapper_group",
    Base.metadata,
    Column("mapper_uid", Uuid, ForeignKey("mapper.uid"), primary_key=True),
    Column(
        "mapper_group_uid", Uuid, ForeignKey("mapper_group.uid"), primary_key=True
    ),
)


class DatabaseMapper(Base, Generic[AttributeType]):
    uid: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), index=True, unique=True)

    attribute_schema_uid: Mapped[UUID] = mapped_column(Uuid, index=True)
    root_attribute_schema_uid: Mapped[UUID] = mapped_column(Uuid, index=True)
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
    literal: Mapped[str | None] = mapped_column(String(128), nullable=True)
    """The one string `expression` matches exactly under `re.match`, or `None`
    when `expression` is a genuine regex (see `literal_key`). Lets the
    resolver find an exact hit via an indexed `(mapper_uid, literal)` lookup
    instead of scanning every expression with `re.match`."""
    attribute: Mapped[AnyAttribute] = mapped_column(attribute_db_type)
    hits: Mapped[int] = mapped_column(Integer, default=0)

    mapper: Mapped[DatabaseMapper[AttributeType]] = relationship(
        DatabaseMapper,
        foreign_keys=mapper_uid,
    )

    __table_args__ = (
        UniqueConstraint(
            "mapper_uid", "expression", name="uq_mapping_item_mapper_uid_expression"
        ),
        Index("ix_mapping_item_mapper_uid_literal", "mapper_uid", "literal"),
    )
    __tablename__ = "mapping_item"

    def __init__(
        self,
        mapper_uid: UUID,
        expression: str,
        attribute: AnyAttribute,
    ):
        super().__init__(
            uid=uuid4(),
            mapper_uid=mapper_uid,
            expression=expression,
            literal=self.literal_key(expression),
            attribute=attribute,
            hits=0,
        )

    def update(self, expression: str, attribute: AnyAttribute):
        self.expression = expression
        self.literal = self.literal_key(expression)
        self.attribute = attribute

    @staticmethod
    def literal_key(expression: str) -> str | None:
        """Return the one string `expression` matches exactly under `re.match`.

        Mapper resolution matches values with ``re.match(expression, value)``
        (anchored at the start only). An expression therefore matches exactly
        one string when it is a start/end-anchored plain literal — e.g. the
        ``^<concept-id>$`` keys that dominate the Diagnose mapper — which lets
        it be resolved by an indexed lookup instead of a regex scan.

        Returns the literal for such expressions, or ``None`` when the
        expression carries any regex machinery (``.*resectie.*``,
        ``^HE[0-9]*``, …) and must go through a regex scan. The check is
        deliberately conservative: anything it is not certain is a plain
        literal falls back to the regex path, so it can never turn a genuine
        regex into a wrong exact match.
        """
        body = expression[1:] if expression.startswith("^") else expression
        if not body.endswith("$"):
            # Without an end anchor, re.match is a prefix match, not an exact one.
            return None
        body = body[:-1]
        # re.escape is a no-op only for strings with no regex metacharacters; if
        # it changed anything (including a trailing backslash escaping our
        # ``$``), the expression is a genuine regex.
        if body == "" or re.escape(body) != body:
            return None
        return body

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
    mappers: Mapped[set[DatabaseMapper]] = relationship(
        "DatabaseMapper",
        secondary=mapper_to_mapper_group,
    )
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
