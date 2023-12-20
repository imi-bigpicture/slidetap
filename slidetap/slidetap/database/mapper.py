"""Mapper specific to a attribute schema containing mapping items."""
from typing import Any, Iterable, List, Optional, Sequence
from uuid import UUID, uuid4

from sqlalchemy import Uuid, select
from sqlalchemy.orm import Mapped

from slidetap.database.attribute import Attribute, MappingItem
from slidetap.database.db import DbBase, NotAllowedActionError, db
from slidetap.database.schema import AttributeSchema


class Mapper(DbBase):
    uid: Mapped[UUID] = db.Column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = db.Column(db.String(128), index=True, unique=True)
    attribute_schema: Mapped[AttributeSchema] = db.relationship(
        AttributeSchema,
        uselist=False,
    )  # type: ignore
    mappings: Mapped[List[MappingItem]] = db.relationship(
        MappingItem,
        single_parent=True,
        foreign_keys=MappingItem.mapper_uid,
        cascade="all, delete-orphan",
    )  # type: ignore

    attribute_schema_uid: Mapped[UUID] = db.Column(
        Uuid, db.ForeignKey("attribute_schema.uid"), index=True, unique=True
    )

    def __init__(
        self,
        name: str,
        attribute_schema: AttributeSchema,
        mappings: Optional[Iterable[MappingItem]] = None,
        add: bool = True,
        commit: bool = True,
    ):
        if mappings is None:
            mappings = []
        if any(
            mapping.attribute.schema_uid != attribute_schema.uid for mapping in mappings
        ):
            raise NotAllowedActionError(
                "Adding a value of another schema is not allowed."
            )
        super().__init__(
            name=name,
            attribute_schema=attribute_schema,
            mappings=mappings,
            add=add,
            commit=commit,
        )

    def add(
        self, expression: str, value: Attribute[Any, Any], commit: bool = True
    ) -> MappingItem:
        if not value.schema == self.attribute_schema:
            raise NotAllowedActionError(
                f"Tried to add mapping with value of schema {value.schema} "
                f"to mapper of schema {self.attribute_schema}. "
                "Adding a value of another schema is not allowed."
            )
        mapping = self.get_mapping(expression)
        if mapping is not None:
            mapping.attribute.set_value(value.value)
            return mapping
        mapping = MappingItem(expression, value)
        self.mappings.append(mapping)
        if commit:
            db.session.commit()
        return mapping

    def add_multiple(
        self,
        expressions: Sequence[str],
        value: Attribute[Any, Any],
        commit: bool = True,
    ) -> List[MappingItem]:
        if not value.schema == self.attribute_schema:
            raise NotAllowedActionError(
                "Adding a value of another schema is not allowed."
            )
        mappings = [self.add(expression, value, False) for expression in expressions]
        if commit:
            db.session.commit()
        return mappings

    def get_mapping_for_value(self, mappable_value: str) -> Optional[MappingItem]:
        mappings = self.mappings
        mapping = next(
            (mapping for mapping in mappings if mapping.matches(mappable_value)),
            None,
        )
        return mapping

    def get_mapping(self, expression: str) -> Optional[MappingItem]:
        return db.session.scalar(
            select(MappingItem).filter_by(mapper_uid=self.uid, expression=expression)
        )

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
    def get_all(cls) -> Sequence["Mapper"]:
        return db.session.scalars(select(Mapper)).all()

    @classmethod
    def get_for_attribute(cls, attribute: Attribute) -> Optional["Mapper"]:
        return cls.get_for_attribute_schema(attribute.schema.uid)

    @classmethod
    def get_for_attribute_schema(cls, attribute_schema_uid: UUID) -> Optional["Mapper"]:
        return db.session.scalars(
            select(Mapper).where(cls.attribute_schema_uid == attribute_schema_uid)
        ).one_or_none()

    def get_mappable_attributes(
        self, only_non_mapped: bool = False
    ) -> Sequence[Attribute]:
        """Return attributes that can be mapped by this mapper."""
        query = select(Attribute).filter(
            Attribute.schema_uid == self.attribute_schema.uid,
            Attribute.mappable_value.isnot(None),
            ~Attribute.parent_mappings.any(),
        )
        if only_non_mapped:
            query.filter_by(mapping_item_uid=None)
        return db.session.scalars(query).all()
