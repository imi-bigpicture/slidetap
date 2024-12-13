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

"""Attributes of different value and schema types."""

from __future__ import annotations

import re
from typing import Generic, Optional
from uuid import UUID, uuid4

from slidetap.database.db import DbBase, db
from slidetap.database.types import attribute_db_type
from slidetap.model.attribute import Attribute, AttributeType
from sqlalchemy import Uuid, select
from sqlalchemy.orm import Mapped, mapped_column


class MappingItem(DbBase, Generic[AttributeType]):
    uid: Mapped[UUID] = db.Column(Uuid, primary_key=True, default=uuid4)
    mapper_uid: Mapped[UUID] = db.Column(Uuid, db.ForeignKey("mapper.uid"))
    expression: Mapped[str] = db.Column(db.String(128))
    attribute: Mapped[Attribute[AttributeType]] = mapped_column(attribute_db_type)

    def __init__(
        self,
        expression: str,
        attribute: Attribute[AttributeType],
        add: bool = True,
        commit: bool = True,
    ):
        super().__init__(
            expression=expression, attribute=attribute, add=add, commit=commit
        )

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def update(self, expression: str, attribute: Attribute[AttributeType]):
        self.expression = expression
        self.attribute = attribute
        db.session.commit()

    @classmethod
    def get_by_uid(cls, uid: UUID):
        return db.session.scalars(select(cls).filter_by(uid=uid)).one()
