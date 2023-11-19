"""Mapper specific to a attribute schema containing mapping items."""
from typing import Any, Iterable, List, Optional, Sequence
from uuid import UUID, uuid4

from sqlalchemy import Uuid, select
from sqlalchemy.orm import Mapped

from slidetap.database.attribute import Attribute, MappingItem
from slidetap.database.db import NotAllowedActionError, db
from slidetap.database.schema import AttributeSchema


class Mapper(db.Model):
    uid: Mapped[UUID] = db.Column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = db.Column(db.String(128))
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
        Uuid, db.ForeignKey("attribute_schema.uid")
    )
    __table_args__ = (
        db.UniqueConstraint("attribute_schema_uid"),
        db.UniqueConstraint("name"),
    )

    def __init__(
        self,
        name: str,
        attribute_schema: AttributeSchema,
        mappings: Optional[Iterable[MappingItem]] = None,
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
            name=name, attribute_schema=attribute_schema, mappings=mappings
        )
        db.session.add(self)
        db.session.commit()

    def add(self, expression: str, value: Attribute[Any, Any]) -> MappingItem:
        if not value.schema_uid == self.attribute_schema_uid:
            raise NotAllowedActionError(
                "Adding a value of another schema is not allowed."
            )
        existing_mapping = self.get_mapping(expression)
        if existing_mapping is not None:
            # TODO Update?
            db.session.delete(existing_mapping)
        mapping_item = MappingItem(expression, value)
        self.mappings.append(mapping_item)
        db.session.commit()
        return mapping_item

    def add_multiple(
        self, expressions: Sequence[str], value: Attribute[Any, Any]
    ) -> List[MappingItem]:
        if not value.schema.uid == self.attribute_schema_uid:
            raise NotAllowedActionError(
                "Adding a value of another schema is not allowed."
            )
        return [self.add(expression, value) for expression in expressions]

    def get_mapping_for_value(self, mappable_value: str) -> Optional[MappingItem]:
        mapping = next(
            (mapping for mapping in self.mappings if mapping.matches(mappable_value)),
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
        return db.session.scalars(select(cls).filter_by(uid=mapper_uid)).one()

    @classmethod
    def get_by_name(cls, name: str) -> Optional["Mapper"]:
        return db.session.scalars(select(cls).filter_by(name=name)).one_or_none()

    @classmethod
    def get_all(cls) -> Sequence["Mapper"]:
        return db.session.scalars(select(Mapper)).all()

    @classmethod
    def get_for_attribute(cls, attribute: Attribute) -> Optional["Mapper"]:
        return cls.get_for_attribute_schema(attribute.schema_uid)

    @classmethod
    def get_for_attribute_schema(cls, attribute_schema_uid: UUID) -> Optional["Mapper"]:
        return db.session.scalars(
            select(Mapper).filter_by(attribute_schema_uid=attribute_schema_uid)
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
