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

"""Project and Sample, Annotations, Observations, Images."""

from __future__ import annotations

from abc import abstractmethod
from pathlib import Path
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Set,
    Type,
    TypeVar,
    Union,
)
from uuid import UUID, uuid4

from sqlalchemy import ScalarResult, Select, Uuid, and_, func, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, attribute_keyed_dict, mapped_column

from slidetap.database.attribute import DatabaseAttribute
from slidetap.database.db import DbBase, NotAllowedActionError, db
from slidetap.database.project import DatabaseProject
from slidetap.database.schema import (
    DatabaseAnnotationSchema,
    DatabaseImageSchema,
    DatabaseItemSchema,
    DatabaseObservationSchema,
    DatabaseSampleSchema,
    ItemValueType,
)
from slidetap.model.image_status import ImageStatus
from slidetap.model.item import (
    Annotation,
    Image,
    ImageFile,
    Item,
    ItemReference,
    Observation,
    Sample,
)
from slidetap.model.table import ColumnSort
from slidetap.model.validation import RelationValidation

ObservationDatabaseItemType = Union[
    "DatabaseAnnotation", "DatabaseImage", "DatabaseSample"
]
ObservationItemType = Union[Annotation, Image, Sample]
DatabaseItemType = TypeVar("DatabaseItemType", bound="DatabaseItem")


class DatabaseItem(DbBase):
    """Base class for an metadata item."""

    uid: Mapped[UUID] = db.Column(Uuid, primary_key=True, default=uuid4)
    identifier: Mapped[str] = db.Column(db.String(128))
    name: Mapped[Optional[str]] = db.Column(db.String(128))
    pseudonym: Mapped[Optional[str]] = db.Column(db.String(128))
    selected: Mapped[bool] = db.Column(db.Boolean, default=True)
    valid_attributes: Mapped[bool] = db.Column(db.Boolean)
    valid_relations: Mapped[bool] = db.Column(db.Boolean)
    item_value_type: Mapped[ItemValueType] = db.Column(db.Enum(ItemValueType))

    # Relations
    attributes: Mapped[Dict[str, DatabaseAttribute[Any, Any, Any]]] = db.relationship(
        DatabaseAttribute,
        collection_class=attribute_keyed_dict("tag"),
        cascade="all, delete-orphan",
    )  # type: ignore
    project: Mapped[DatabaseProject] = db.relationship("DatabaseProject")  # type: ignore

    # For relations
    schema_uid: Mapped[UUID] = db.Column(Uuid)
    project_uid: Mapped[UUID] = db.Column(Uuid, db.ForeignKey("project.uid"))

    # From relations
    __table_args__ = (db.ForeignKeyConstraint([schema_uid], [DatabaseItemSchema.uid]),)
    __mapper_args__ = {
        "polymorphic_on": "item_value_type",
    }
    __tablename__ = "item"

    def __init__(
        self,
        project: DatabaseProject,
        schema: DatabaseItemSchema,
        identifier: str,
        name: Optional[str],
        pseudonym: Optional[str],
        attributes: Optional[Dict[str, DatabaseAttribute]],
        selected: bool,
        add: bool,
        uid: Optional[UUID] = None,
    ):
        """Create and add an item to the database.

        Parameters
        ----------
        project: Project
            Project the item belongs to.
        schema: ItemSchema
            The schema of the item.
        identifier: str
            The identifier of the item.
        name: Optional[str]
            Optional (short) name of the item.
        pseudonym: Optional[str]
            Optional pseudonym of the item.
        attributes: Optional[Dict[str, Any]]
            Optional dictionary of attributes for the item.
        selected: bool
            Whether the item is selected.
        add: bool
            Add the item to the database.
        uid: Optional[UUID] = None
            Optional uid of the item.
        """
        if attributes is None:
            attributes = {}
        else:
            attributes = {
                attribute.tag: attribute
                for attribute in attributes.values()
                if attribute is not None
            }
        super().__init__(
            add=add,
            commit=False,
            project=project,
            schema=schema,
            identifier=identifier,
            name=name,
            pseudonym=pseudonym,
            attributes=attributes,
            selected=selected,
            uid=uid,
        )

        # self.valid_attributes = all(
        #     validation.valid for validation in self._validate_attributes()
        # )

    @classmethod
    def get_or_create_from_model(
        cls,
        model: Item,
        append_relations: bool = False,
    ) -> DatabaseItem:
        if isinstance(model, Annotation):
            return DatabaseAnnotation.get_or_create_from_model(model, append_relations)
        if isinstance(model, Image):
            return DatabaseImage.get_or_create_from_model(model, append_relations)
        if isinstance(model, Observation):
            return DatabaseObservation.get_or_create_from_model(model, append_relations)
        if isinstance(model, Sample):
            return DatabaseSample.get_or_create_from_model(model, append_relations)
        raise ValueError(f"Unknown model type {model}.")

    @hybrid_property
    @abstractmethod
    def schema(self) -> DatabaseItemSchema:
        raise NotImplementedError()

    @hybrid_property
    def schema_name(self) -> str:
        return self.schema.name

    @hybrid_property
    def schema_display_name(self) -> str:
        return self.schema.display_name

    @hybrid_property
    def valid(self) -> bool:
        return self.valid_attributes and self.valid_relations

    # @property
    # def validation(self) -> ItemValidation:
    #     non_valid_attributes = [
    #         attribute.validation
    #         for attribute in self.attributes.values()
    #         if not attribute.valid
    #     ]
    #     non_valid_relations = []
    #     return ItemValidation(
    #         valid=self.valid,
    #         uid=self.uid,
    #         display_name=self.identifier,
    #         non_valid_attributes=non_valid_attributes,
    #         non_valid_relations=non_valid_relations,
    #     )

    @property
    @abstractmethod
    def model(self) -> Item:
        raise NotImplementedError()

    @property
    def reference(self) -> ItemReference:
        return ItemReference(
            uid=self.uid,
            identifier=self.identifier,
            name=self.name,
            schema_display_name=self.schema.display_name,
            schema_uid=self.schema.uid,
        )

    def commit(self):
        db.session.commit()

    def set_select(self, value: bool, commit: bool = True):
        self.select(value)
        if commit:
            db.session.commit()

    def set_attributes(
        self, attributes: Dict[str, DatabaseAttribute], commit: bool = True
    ) -> None:
        for tag, attribute in attributes.items():
            if tag in self.attributes:
                self.attributes[tag].set_value(attribute.value, commit=False)
            else:
                self.attributes[tag] = attribute
        if commit:
            db.session.commit()

    # def update_attributes(
    #     self, attributes: Dict[str, DatabaseAttribute], commit: bool = True
    # ) -> None:
    #     for tag, attribute in attributes.items():
    #         if tag in self.attributes:
    #             self.attributes[tag].set_value(attribute.value, commit=False)
    #         else:
    #             self.attributes[tag] = attribute
    #     self.attributes.update(attributes)
    #     # self.validate(attributes=True)
    #     if commit:
    #         db.session.commit()

    def set_name(self, name: Optional[str], commit: bool = True) -> None:
        self.name = name
        if commit:
            db.session.commit()

    def set_identifier(self, identifier: str, commit: bool = True) -> None:
        self.identifier = identifier
        if commit:
            db.session.commit()

    # def validate(
    #     self, relations: bool = True, attributes: bool = True, commit: bool = True
    # ) -> bool:
    #     # pre_state = self.valid
    #     # current_app.logger.debug(
    #     #     f"Validating item {self.uid} with pre state {pre_state}."
    #     # )
    #     if relations:
    #         relation_validations = self._validate_relations()
    #         self.valid_relations = all(
    #             relation.valid for relation in relation_validations
    #         )
    #     if attributes:
    #         attribute_validations = self._validate_attributes(re_validate=True)
    #         self.valid_attributes = all(
    #             attribute.valid for attribute in attribute_validations
    #         )
    #     if commit:
    #         db.session.commit()
    #     # if pre_state != self.valid:
    #     #     current_app.logger.debug(f"Item {self.uid} is now {self.valid}.")
    #     # else:
    #     #     current_app.logger.debug(f"Item {self.uid} is still {self.valid}.")

    #     return self.valid

    @abstractmethod
    def select(self, value: bool):
        """Should select or de-select the item."""
        raise NotImplementedError()

    @abstractmethod
    def copy(self) -> DatabaseItem:
        """Should copy the item."""
        raise NotImplementedError()

    @abstractmethod
    def _validate_relations(self) -> Iterable[RelationValidation]:
        """Should return True if the item (excluding attributes) are valid."""
        raise NotImplementedError()

    @classmethod
    def add(cls, item: DatabaseItem):
        if item.uid is not None:
            raise ValueError("Item already added.")
        item.uid = uuid4()
        db.session.add(item)
        db.session.commit()

    @classmethod
    def get(cls: Type[DatabaseItemType], uid: UUID) -> DatabaseItemType:
        """Return item by id."""
        item = cls.get_optional(uid)
        if item is None:
            raise ValueError(f"Item with uid {uid} not found.")
        return item

    @classmethod
    def get_optional(
        cls: Type[DatabaseItemType], uid: UUID
    ) -> Optional[DatabaseItemType]:
        """Return item by id."""
        return db.session.get(cls, uid)

    @classmethod
    def delete_for_project_and_schema(
        cls,
        project: Union[UUID, "DatabaseProject"],
        schema: Union[UUID, DatabaseItemSchema],
        only_non_selected=False,
    ):
        if isinstance(project, DatabaseProject):
            project = project.uid
        if isinstance(schema, DatabaseItemSchema):
            schema = schema.uid
        items = cls.get_for_project(project, schema)
        for item in items:
            if only_non_selected and item.selected or item in db.session.deleted:
                continue
            db.session.delete(item)
        db.session.commit()

    @classmethod
    def get_for_project(
        cls: Type[DatabaseItemType],
        project: Union[UUID, "DatabaseProject"],
        schema: Optional[Union[UUID, DatabaseItemSchema]] = None,
        start: Optional[int] = None,
        size: Optional[int] = None,
        identifier_filter: Optional[str] = None,
        attributes_filters: Optional[Dict[str, str]] = None,
        sorting: Optional[Iterable[ColumnSort]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> Iterable[DatabaseItemType]:
        if isinstance(project, DatabaseProject):
            project = project.uid
        if isinstance(schema, DatabaseItemSchema):
            schema = schema.uid
        query = cls._query_for_schema(
            select(cls),
            project=project,
            schema=schema,
            identifier_filter=identifier_filter,
            attributes_filters=attributes_filters,
            selected=selected,
            valid=valid,
        )
        if sorting is not None:
            for sort in sorting:
                if not sort.is_attribute:
                    if sort.column == "identifier":
                        sort_by = DatabaseItem.identifier
                    elif sort.column == "valid":
                        sort_by = DatabaseItem.valid
                    elif sort.column == "status" and issubclass(cls, DatabaseImage):
                        sort_by = DatabaseImage.status
                    elif sort.column == "message" and issubclass(cls, DatabaseImage):
                        sort_by = DatabaseImage.status_message
                    else:
                        raise NotImplementedError(f"Got unknown column {sort.column}.")
                    if sort.descending:
                        sort_by = sort_by.desc()
                    query = query.order_by(sort_by)
                else:
                    sort_by = DatabaseAttribute.display_value
                    if sort.descending:
                        sort_by = sort_by.desc()
                    query = (
                        query.join(DatabaseAttribute)
                        .where(DatabaseAttribute.schema.has(tag=sort.column))
                        .order_by(sort_by)
                    )

        if start is not None:
            query = query.offset(start)
        if size is not None:
            query = query.limit(size)
        return db.session.scalars(query)

    @classmethod
    def get_count_for_project(
        cls,
        project: Union[UUID, "DatabaseProject"],
        schema: Optional[Union[UUID, DatabaseItemSchema]] = None,
        identifier_filter: Optional[str] = None,
        attributes_filters: Optional[Dict[str, str]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> int:
        query = cls._query_for_schema(
            select(func.count(cls.uid)),
            project=project,
            schema=schema,
            identifier_filter=identifier_filter,
            attributes_filters=attributes_filters,
            selected=selected,
            valid=valid,
        )
        return db.session.scalars(query).one()

    def get_attribute(self, key: str) -> DatabaseAttribute[Any, Any, Any]:
        return self.attributes[key]

    @classmethod
    def _query_for_schema(
        cls,
        query: Select,
        project: Union[UUID, "DatabaseProject"],
        schema: Optional[Union[UUID, DatabaseItemSchema]] = None,
        identifier_filter: Optional[str] = None,
        attributes_filters: Optional[Dict[str, str]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> Select:
        if isinstance(project, DatabaseProject):
            project = project.uid
        if isinstance(schema, DatabaseItemSchema):
            schema = schema.uid
        query = query.filter_by(project_uid=project)
        if schema is not None:
            query = query.filter_by(schema_uid=schema)
        if identifier_filter is not None:
            query = query.filter(DatabaseItem.identifier.icontains(identifier_filter))
        if attributes_filters is not None:
            for tag, value in attributes_filters.items():
                query = query.filter(
                    DatabaseItem.attributes.any(
                        and_(
                            DatabaseAttribute.display_value.icontains(value),
                            DatabaseAttribute.schema.has(tag=tag),
                        )
                    )
                )
        if selected is not None:
            query = query.filter_by(selected=selected)
        if valid is not None:
            query = query.filter_by(valid=valid)
        return query


class DatabaseObservation(DatabaseItem):
    """An observation item. Is related to an image or a sample."""

    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("item.uid", ondelete="CASCADE"), primary_key=True
    )

    # For relations
    image_uid: Mapped[Optional[UUID]] = mapped_column(db.ForeignKey("image.uid"))
    sample_uid: Mapped[Optional[UUID]] = mapped_column(db.ForeignKey("sample.uid"))
    annotation_uid: Mapped[Optional[UUID]] = mapped_column(
        db.ForeignKey("annotation.uid")
    )

    # Relationships
    schema: Mapped[DatabaseObservationSchema] = db.relationship(DatabaseObservationSchema)  # type: ignore
    image: Mapped[Optional[DatabaseImage]] = db.relationship(
        "DatabaseImage", back_populates="observations", foreign_keys=[image_uid]
    )  # type: ignore
    sample: Mapped[Optional[DatabaseSample]] = db.relationship(
        "DatabaseSample", back_populates="observations", foreign_keys=[sample_uid]
    )  # type: ignore
    annotation: Mapped[Optional[DatabaseAnnotation]] = db.relationship(
        "DatabaseAnnotation",
        back_populates="observations",
        foreign_keys=[annotation_uid],
    )  # type: ignore

    # From relations

    __mapper_args__ = {
        "polymorphic_identity": ItemValueType.OBSERVATION,
    }
    __tablename__ = "observation"

    def __init__(
        self,
        project: DatabaseProject,
        schema: DatabaseObservationSchema,
        identifier: str,
        item: Optional[ObservationDatabaseItemType] = None,
        attributes: Optional[Dict[str, DatabaseAttribute]] = None,
        name: Optional[str] = None,
        pseudonym: Optional[str] = None,
        selected: bool = True,
        uid: Optional[UUID] = None,
        add: bool = True,
        commit: bool = True,
    ):
        super().__init__(
            project=project,
            schema=schema,
            identifier=identifier,
            name=name,
            pseudonym=pseudonym,
            selected=selected,
            attributes=attributes,
            add=add,
            uid=uid,
        )
        if item is not None:
            self.set_item(item, commit=False)
        if commit:
            db.session.commit()

    @classmethod
    def get_or_create_from_model(
        cls, model: Observation, append_relations: bool = False
    ) -> "DatabaseObservation":
        existing = db.session.get(cls, model.uid)
        if existing is not None:
            return existing
        if model.item is not None:
            item = DatabaseItem.get(model.item.uid)
            if not isinstance(
                item, (DatabaseImage, DatabaseSample, DatabaseAnnotation)
            ):
                raise ValueError(f"Item {item} is not an image, sample or annotation.")
        else:
            item = None
        attributes = {
            tag: DatabaseAttribute.from_model(attribute)
            for tag, attribute in model.attributes.items()
        }
        return cls(
            project=DatabaseProject.get(model.project_uid),
            schema=DatabaseObservationSchema.get(model.schema_uid),
            identifier=model.identifier,
            item=item,
            attributes=attributes,
            name=model.name,
            pseudonym=model.pseudonym,
            selected=model.selected,
            uid=model.uid,
        )

    @hybrid_property
    def item(self) -> Union["DatabaseImage", "DatabaseSample", "DatabaseAnnotation"]:
        """Return the item the observation is related to, either an image or
        a sample."""
        if self.image is not None:
            return self.image
        if self.sample is not None:
            return self.sample
        raise ValueError("Image or sample should be set.")

    @property
    def model(self) -> Observation:
        return Observation(
            uid=self.uid,
            identifier=self.identifier,
            name=self.name,
            pseudonym=self.pseudonym,
            selected=self.selected,
            valid=self.valid_attributes and self.valid_relations,
            valid_attributes=self.valid_attributes,
            valid_relations=self.valid_relations,
            attributes={
                key: attribute.model for key, attribute in self.attributes.items()
            },
            project_uid=self.project.uid,
            schema_display_name=self.schema.display_name,
            schema_uid=self.schema.uid,
            item=self.item.reference,
        )

    def set_item(
        self,
        item: Union["DatabaseImage", "DatabaseSample", "DatabaseAnnotation"],
        commit: bool = True,
    ) -> None:
        if isinstance(item, DatabaseImage):
            self.image = item
        elif isinstance(item, DatabaseSample):
            self.sample = item
        elif isinstance(item, DatabaseAnnotation):
            self.annotation = item
        else:
            raise ValueError("Item should be an image, sample or annotation.")
        # self.validate(attributes=False)
        # item.validate(attributes=False)
        if commit:
            db.session.commit()

    def select(self, value: bool):
        self.selected = value
        if isinstance(self.item, DatabaseSample):
            self.item.select_from_child(value, self.uid)
        else:
            self.item.select(value)

    def select_from_sample(self, value: bool):
        self.selected = value

    def copy(self) -> DatabaseObservation:
        return DatabaseObservation(
            project=self.project,
            schema=self.schema,
            identifier=f"{self.identifier} (copy)",
            item=self.item,
            attributes={
                attribute.tag: attribute.copy()
                for attribute in self.attributes.values()
            },
            name=f"{self.name} (copy)" if self.name else None,
            pseudonym=f"{self.pseudonym} (copy)" if self.pseudonym else None,
            add=False,
            commit=False,
        )


class DatabaseAnnotation(DatabaseItem):
    """An annotation item. Is related to an image."""

    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("item.uid", ondelete="CASCADE"), primary_key=True
    )

    # For relations
    image_uid: Mapped[UUID] = mapped_column(db.ForeignKey("image.uid"))

    # Relationships
    schema: Mapped[DatabaseAnnotationSchema] = db.relationship(DatabaseAnnotationSchema)  # type: ignore
    image: Mapped[Optional[DatabaseImage]] = db.relationship(
        "DatabaseImage", back_populates="annotations", foreign_keys=[image_uid]
    )  # type: ignore
    observations: Mapped[List[DatabaseObservation]] = db.relationship(
        DatabaseObservation,
        back_populates="annotation",
        foreign_keys=[DatabaseObservation.annotation_uid],
    )  # type: ignore

    __mapper_args__ = {
        "polymorphic_identity": ItemValueType.ANNOTATION,
    }
    __tablename__ = "annotation"

    def __init__(
        self,
        project: DatabaseProject,
        schema: DatabaseAnnotationSchema,
        identifier: str,
        image: Optional[DatabaseImage] = None,
        attributes: Optional[Dict[str, DatabaseAttribute]] = None,
        name: Optional[str] = None,
        pseudonym: Optional[str] = None,
        selected: bool = True,
        uid: Optional[UUID] = None,
        add: bool = True,
        commit: bool = True,
    ):
        super().__init__(
            project=project,
            schema=schema,
            identifier=identifier,
            attributes=attributes,
            name=name,
            pseudonym=pseudonym,
            selected=selected,
            uid=uid,
            add=add,
        )
        if image is not None:
            self.set_image(image, commit=False)
        if commit:
            db.session.commit()

    @classmethod
    def get_or_create_from_model(
        cls, model: Annotation, append_relations: bool = False
    ) -> "DatabaseAnnotation":
        existing = db.session.get(cls, model.uid)
        if existing is not None:
            return existing
        if model.image is not None:
            image = DatabaseImage.get(model.image.uid)
        else:
            image = None
        attributes = {
            tag: DatabaseAttribute.from_model(attribute)
            for tag, attribute in model.attributes.items()
        }
        return cls(
            project=DatabaseProject.get(model.project_uid),
            schema=DatabaseAnnotationSchema.get(model.schema_uid),
            identifier=model.identifier,
            image=image,
            attributes=attributes,
            name=model.name,
            pseudonym=model.pseudonym,
            selected=model.selected,
            uid=model.uid,
        )

    @property
    def model(self) -> Annotation:
        return Annotation(
            uid=self.uid,
            identifier=self.identifier,
            name=self.name,
            pseudonym=self.pseudonym,
            selected=self.selected,
            valid=self.valid_attributes and self.valid_relations,
            valid_attributes=self.valid_attributes,
            valid_relations=self.valid_relations,
            attributes={
                key: attribute.model for key, attribute in self.attributes.items()
            },
            project_uid=self.project.uid,
            schema_display_name=self.schema.display_name,
            schema_uid=self.schema.uid,
            image=self.image.reference if self.image is not None else None,
            obseration=[observation.reference for observation in self.observations],
        )

    def set_image(self, image: Optional[DatabaseImage], commit: bool = True):
        self.image = image
        # self.validate(attributes=False)
        # image.validate(attributes=False)
        if commit:
            db.session.commit()

    def copy(self) -> DatabaseItem:
        return DatabaseAnnotation(
            project=self.project,
            schema=self.schema,
            identifier=f"{self.identifier} (copy)",
            image=self.image,
            attributes={
                attribute.tag: attribute.copy()
                for attribute in self.attributes.values()
            },
            name=f"{self.name} (copy)" if self.name else None,
            pseudonym=f"{self.pseudonym} (copy)" if self.pseudonym else None,
            add=False,
            commit=False,
        )


class DatabaseImageFile(DbBase):
    """Represents a file stored for an image."""

    uid: Mapped[UUID] = db.Column(Uuid, primary_key=True, default=uuid4)
    filename: Mapped[str] = db.Column(db.String(512))

    # For relations
    # TODO should optional be allowed here?
    image_uid: Mapped[Optional[UUID]] = mapped_column(db.ForeignKey("image.uid"))

    # Relations
    image: Mapped[Optional[DatabaseImage]] = db.relationship(
        "DatabaseImage",
        back_populates="files",
        foreign_keys=[image_uid],
    )  # type: ignore

    __tablename__ = "image_file"

    def __init__(self, filename: str, add: bool = True, commit: bool = True):
        """A file stored for a image.

        Parameters
        ----------
        filename: Name of file relative to image folder.

        """
        super().__init__(filename=filename, add=add, commit=commit)

    @property
    def model(self) -> ImageFile:
        return ImageFile(uid=self.uid, filename=self.filename)


class DatabaseImage(DatabaseItem):
    # Table for mapping many-to-many samples to images
    sample_to_image = db.Table(
        "sample_to_image",
        db.Column(
            "sample_uid",
            Uuid,
            db.ForeignKey("sample.uid"),
            primary_key=True,
        ),
        db.Column(
            "image_uid",
            Uuid,
            db.ForeignKey("image.uid"),
            primary_key=True,
        ),
    )
    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("item.uid", ondelete="CASCADE"), primary_key=True
    )
    external_identifier: Mapped[Optional[str]] = db.Column(db.String(128))

    folder_path: Mapped[str] = db.Column(db.String(512))
    thumbnail_path: Mapped[str] = db.Column(db.String(512))

    status: Mapped[ImageStatus] = db.Column(db.Enum(ImageStatus))
    status_message: Mapped[Optional[str]] = db.Column(db.String(512))
    # Relationship
    schema: Mapped[DatabaseImageSchema] = db.relationship(DatabaseImageSchema)  # type: ignore
    samples: Mapped[List[DatabaseSample]] = db.relationship(
        "DatabaseSample", secondary=sample_to_image, back_populates="images"
    )  # type: ignore
    annotations: Mapped[List[DatabaseAnnotation]] = db.relationship(
        DatabaseAnnotation,
        back_populates="image",
        foreign_keys=[DatabaseAnnotation.image_uid],
    )  # type: ignore
    observations: Mapped[List[DatabaseObservation]] = db.relationship(
        DatabaseObservation,
        back_populates="image",
        foreign_keys=[DatabaseObservation.image_uid],
    )  # type: ignore
    files: Mapped[List[DatabaseImageFile]] = db.relationship(
        DatabaseImageFile,
        back_populates="image",
        foreign_keys=[DatabaseImageFile.image_uid],
        cascade="all, delete-orphan",
    )  # type: ignore

    __mapper_args__ = {
        "polymorphic_identity": ItemValueType.IMAGE,
    }
    __tablename__ = "image"

    def __init__(
        self,
        project: DatabaseProject,
        schema: DatabaseImageSchema,
        identifier: str,
        samples: Optional[Union["DatabaseSample", Iterable["DatabaseSample"]]] = None,
        attributes: Optional[Dict[str, DatabaseAttribute]] = None,
        name: Optional[str] = None,
        pseudonym: Optional[str] = None,
        external_identifier: Optional[str] = None,
        selected: bool = True,
        uid: Optional[UUID] = None,
        add: bool = True,
        commit: bool = True,
    ):
        self.status = ImageStatus.NOT_STARTED
        self.external_identifier = external_identifier
        super().__init__(
            project=project,
            schema=schema,
            identifier=identifier,
            attributes=attributes,
            name=name,
            pseudonym=pseudonym,
            selected=selected,
            uid=uid,
            add=add,
        )
        if samples is not None:
            if not isinstance(samples, Iterable):
                samples = [samples]
            self.set_samples(samples, commit=False)
        if commit:
            db.session.commit()

    @classmethod
    def get_or_create_from_model(
        cls, model: Image, append_relations: bool = False
    ) -> "DatabaseImage":
        existing = db.session.get(cls, model.uid)
        if existing is not None:
            return existing
        if model.samples is not None:
            samples = (DatabaseSample.get(sample.uid) for sample in model.samples)
        else:
            samples = None

        attributes = {
            tag: DatabaseAttribute.from_model(attribute)
            for tag, attribute in model.attributes.items()
        }
        return cls(
            project=DatabaseProject.get(model.project_uid),
            schema=DatabaseImageSchema.get(model.schema_uid),
            identifier=model.identifier,
            samples=samples,
            attributes=attributes,
            name=model.name,
            pseudonym=model.pseudonym,
            external_identifier=model.external_identifier,
            selected=model.selected,
            uid=model.uid,
        )

    @hybrid_property
    def valid(self) -> bool:
        return self.valid_attributes and self.valid_relations and not self.failed

    @hybrid_property
    def not_started(self) -> bool:
        return self.status == ImageStatus.NOT_STARTED

    @hybrid_property
    def downloading(self) -> bool:
        return self.status == ImageStatus.DOWNLOADING

    @hybrid_property
    def downloading_failed(self) -> bool:
        return self.status == ImageStatus.DOWNLOADING_FAILED

    @hybrid_property
    def downloaded(self) -> bool:
        return self.status == ImageStatus.DOWNLOADED

    @hybrid_property
    def pre_processing(self) -> bool:
        return self.status == ImageStatus.PRE_PROCESSING

    @hybrid_property
    def pre_processing_failed(self) -> bool:
        return self.status == ImageStatus.PRE_PROCESSING_FAILED

    @hybrid_property
    def pre_processed(self) -> bool:
        return self.status == ImageStatus.PRE_PROCESSED

    @hybrid_property
    def post_processing(self) -> bool:
        return self.status == ImageStatus.POST_PROCESSING

    @hybrid_property
    def post_precssing_failed(self) -> bool:
        return self.status == ImageStatus.POST_PROCESSING_FAILED

    @hybrid_property
    def post_processed(self) -> bool:
        return self.status == ImageStatus.POST_PROCESSED

    @hybrid_property
    def failed(self) -> bool:
        return (
            self.downloading_failed
            or self.pre_processing_failed
            or self.post_precssing_failed
        )

    @property
    def model(self) -> Image:
        return Image(
            uid=self.uid,
            identifier=self.identifier,
            name=self.name,
            pseudonym=self.pseudonym,
            selected=self.selected,
            valid=self.valid_attributes and self.valid_relations,
            valid_attributes=self.valid_attributes,
            valid_relations=self.valid_relations,
            attributes={
                key: attribute.model for key, attribute in self.attributes.items()
            },
            project_uid=self.project.uid,
            schema_display_name=self.schema.display_name,
            schema_uid=self.schema.uid,
            external_identifier=self.external_identifier,
            folder_path=self.folder_path,
            thumbnail_path=self.thumbnail_path,
            status=self.status,
            status_message=self.status_message,
            files=[file.model for file in self.files],
            samples=[sample.reference for sample in self.samples],
            annotations=[annotation.reference for annotation in self.annotations],
            observations=[observation.reference for observation in self.observations],
        )

    def set_as_downloading(self):
        if not self.not_started:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.NOT_STARTED} image as "
                f"{ImageStatus.DOWNLOADING}, was {self.status}."
            )
        self.status = ImageStatus.DOWNLOADING
        db.session.commit()

    def reset_as_not_started(self):
        if not self.downloading_failed:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.DOWNLOADING_FAILED} image as {ImageStatus.NOT_STARTED}, was {self.status}."
            )
        self.status = ImageStatus.NOT_STARTED
        db.session.commit()

    def set_as_downloading_failed(self):
        if not self.downloading:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.DOWNLOADING} image as "
                f"{ImageStatus.DOWNLOADING_FAILED}, was {self.status}."
            )
        self.status = ImageStatus.DOWNLOADING_FAILED
        # self.valid = False
        db.session.commit()

    def set_as_downloaded(self):
        if not self.downloading:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.DOWNLOADING} image as "
                f"{ImageStatus.DOWNLOADED}, was {self.status}."
            )
        self.status = ImageStatus.DOWNLOADED
        db.session.commit()

    def set_as_pre_processing(self):
        if not self.downloaded:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.DOWNLOADED} image as "
                f"{ImageStatus.PRE_PROCESSING}, was {self.status}."
            )
        self.status = ImageStatus.PRE_PROCESSING
        db.session.commit()

    def set_as_pre_processing_failed(self):
        if not self.pre_processing:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.PRE_PROCESSING} image as "
                f"{ImageStatus.PRE_PROCESSING_FAILED}, was {self.status}."
            )
        self.status = ImageStatus.PRE_PROCESSING_FAILED
        db.session.commit()

    def set_as_pre_processed(self, force: bool = False):
        if not self.pre_processing and not (force and self.post_processing):
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.PRE_PROCESSING} image as "
                f"{ImageStatus.PRE_PROCESSED}, was {self.status}."
            )
        self.status = ImageStatus.PRE_PROCESSED
        db.session.commit()

    def reset_as_downloaded(self):
        if not self.pre_processing_failed:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.PRE_PROCESSING_FAILED} image as "
                f"{ImageStatus.DOWNLOADED}, was {self.status}."
            )
        self.status = ImageStatus.DOWNLOADED
        db.session.commit()

    def reset_as_pre_processed(self):
        if not self.post_precssing_failed:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.POST_PROCESSING_FAILED} image as "
                f"{ImageStatus.PRE_PROCESSED}, was {self.status}."
            )
        self.status = ImageStatus.PRE_PROCESSED
        db.session.commit()

    def set_as_post_processing(self):
        if not self.pre_processed:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.PRE_PROCESSED} image as "
                f"{ImageStatus.POST_PROCESSING}, was {self.status}."
            )
        self.status = ImageStatus.POST_PROCESSING
        db.session.commit()

    def set_as_post_processing_failed(self):
        if not self.post_processing:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.POST_PROCESSING} image as "
                f"{ImageStatus.POST_PROCESSING_FAILED}, was {self.status}."
            )
        self.status = ImageStatus.POST_PROCESSING_FAILED
        db.session.commit()

    def set_as_post_processed(self):
        if not self.post_processing:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.POST_PROCESSING} image as "
                f"{ImageStatus.POST_PROCESSED}, was {self.status}."
            )
        self.status = ImageStatus.POST_PROCESSED
        db.session.commit()

    def select(self, value: bool):
        self.selected = value
        for sample in self.samples:
            sample.select_from_parent(self.selected)
        for observation in self.observations:
            observation.select(self.selected)
        for annotation in self.annotations:
            annotation.select(self.selected)

    def select_from_sample(self, value: bool):
        if not value:
            self.selected = False
        elif all(parent.selected for parent in self.samples):
            self.selected = True

    @classmethod
    def get_or_add(
        cls,
        identifier: str,
        schema: DatabaseImageSchema,
        samples: Sequence["DatabaseSample"],
        attributes: Optional[Dict[str, DatabaseAttribute]] = None,
        name: Optional[str] = None,
        pseudonym: Optional[str] = None,
        external_identifier: Optional[str] = None,
        commit: bool = True,
    ) -> "DatabaseImage":
        # Check if any of the samples already have the image
        image = next(
            (
                sample
                for sample in (sample.get_image(identifier) for sample in samples)
                if sample is not None
            ),
            None,
        )

        if image is not None:
            # Add all samples to image
            image.set_samples(samples, commit=commit)
        else:
            # Create a new image
            image = cls(
                project=samples[0].project,
                schema=schema,
                identifier=identifier,
                attributes=attributes,
                samples=samples,
                name=name,
                pseudonym=pseudonym,
                external_identifier=external_identifier,
                commit=commit,
            )
        return image

    def set_folder_path(self, path: Path, commit: bool = False):
        self.folder_path = str(path)
        if commit:
            db.session.commit()

    def set_thumbnail_path(self, path: Path, commit: bool = False):
        self.thumbnail_path = str(path)
        if commit:
            db.session.commit()

    def set_files(self, files: List[DatabaseImageFile], commit: bool = True):
        self.files = files
        if commit:
            db.session.commit()

    def set_samples(self, samples: Iterable[DatabaseSample], commit: bool = True):
        self.samples = list(samples)
        # self.validate(attributes=False)
        # for sample in self.samples:
        #     sample.validate(attributes=False)
        if commit:
            db.session.commit()

    @classmethod
    def get_images_with_thumbnails(
        cls, project: DatabaseProject
    ) -> Iterable["DatabaseImage"]:
        """Return image id with thumbnail."""
        return db.session.scalars(
            select(DatabaseImage).filter(
                cls.project_uid == project.uid, cls.thumbnail_path.isnot(None)
            )
        )

    def copy(self) -> DatabaseImage:
        return DatabaseImage(
            project=self.project,
            schema=self.schema,
            identifier=f"{self.identifier} (copy)",
            samples=self.samples,
            attributes={
                attribute.tag: attribute.copy()
                for attribute in self.attributes.values()
            },
            name=f"{self.name} (copy)" if self.name else None,
            pseudonym=f"{self.pseudonym} (copy)" if self.pseudonym else None,
            add=False,
            commit=False,
        )

    @classmethod
    def get_images_for_project(
        cls,
        project_uid: UUID,
        include_status: Iterable[ImageStatus] = [],
        exclude_status: Iterable[ImageStatus] = [],
        selected: Optional[bool] = None,
    ) -> Iterable[DatabaseImage]:
        return cls._get_images_for_project(
            project_uid, include_status, exclude_status, selected
        )

    @classmethod
    def get_first_image_for_project(
        cls,
        project_uid: UUID,
        include_status: Iterable[ImageStatus] = [],
        exclude_status: Iterable[ImageStatus] = [],
        selected: Optional[bool] = None,
    ) -> Optional[DatabaseImage]:
        query = cls._get_images_for_project(
            project_uid, include_status, exclude_status, selected
        )
        return query.first()

    @classmethod
    def _get_images_for_project(
        cls,
        project_uid: UUID,
        include_status: Iterable[ImageStatus] = [],
        exclude_status: Iterable[ImageStatus] = [],
        selected: Optional[bool] = None,
    ) -> ScalarResult[DatabaseImage]:
        query = select(DatabaseImage).filter(DatabaseImage.project_uid == project_uid)
        for item in include_status:
            query = query.filter(DatabaseImage.status == item)
        for item in exclude_status:
            query = query.filter(DatabaseImage.status != item)
        if selected is not None:
            query = query.filter(DatabaseImage.selected == selected)
        return db.session.scalars(query)


class DatabaseSample(DatabaseItem):
    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("item.uid", ondelete="CASCADE"), primary_key=True
    )

    # Table for mapping many-to-many samples to samples.
    sample_to_sample = db.Table(
        "sample_to_sample",
        db.Column(
            "parent_uid",
            Uuid,
            db.ForeignKey("sample.uid"),
            primary_key=True,
        ),
        db.Column(
            "child_uid",
            Uuid,
            db.ForeignKey("sample.uid"),
            primary_key=True,
        ),
    )

    # Relations
    children: Mapped[List[DatabaseSample]] = db.relationship(
        "DatabaseSample",
        secondary=sample_to_sample,
        primaryjoin=(uid == sample_to_sample.c.parent_uid),
        secondaryjoin=(uid == sample_to_sample.c.child_uid),
        back_populates="parents",
        cascade="all, delete",
    )  # type: ignore
    parents: Mapped[List[DatabaseSample]] = db.relationship(
        "DatabaseSample",
        secondary=sample_to_sample,
        primaryjoin=(uid == sample_to_sample.c.child_uid),
        secondaryjoin=(uid == sample_to_sample.c.parent_uid),
        back_populates="children",
    )  # type: ignore
    images: Mapped[List[DatabaseImage]] = db.relationship(
        DatabaseImage, secondary=DatabaseImage.sample_to_image, back_populates="samples"
    )  # type: ignore
    observations: Mapped[List[DatabaseObservation]] = db.relationship(
        DatabaseObservation,
        back_populates="sample",
        foreign_keys=[DatabaseObservation.sample_uid],
    )  # type: ignore

    schema: Mapped[DatabaseSampleSchema] = db.relationship(DatabaseSampleSchema)  # type: ignore

    __mapper_args__ = {
        "polymorphic_identity": ItemValueType.SAMPLE,
    }
    __tablename__ = "sample"

    def __init__(
        self,
        project: DatabaseProject,
        schema: DatabaseSampleSchema,
        identifier: str,
        parents: Optional[Union["DatabaseSample", Iterable["DatabaseSample"]]] = None,
        children: Optional[Union["DatabaseSample", Iterable["DatabaseSample"]]] = None,
        attributes: Optional[Dict[str, DatabaseAttribute]] = None,
        name: Optional[str] = None,
        pseudonym: Optional[str] = None,
        selected: bool = True,
        uid: Optional[UUID] = None,
        add: bool = True,
        commit: bool = True,
    ):
        super().__init__(
            project=project,
            schema=schema,
            identifier=identifier,
            name=name,
            pseudonym=pseudonym,
            attributes=attributes,
            selected=selected,
            add=add,
            uid=uid,
        )
        if parents is not None:
            if not isinstance(parents, Iterable):
                parents = [parents]
            self.set_parents(parents, commit=False)
        if children is not None:
            if not isinstance(children, Iterable):
                children = [children]
            self.set_children(children, commit=False)

        if commit:
            db.session.commit()

    @classmethod
    def get_or_create_from_model(
        cls, model: Sample, append_relations: bool = False
    ) -> "DatabaseSample":
        existing = db.session.get(cls, model.uid)
        if existing is not None:
            if append_relations:
                existing_parents = {parent.identifier for parent in existing.parents}
                for parent in model.parents:
                    if parent.identifier not in existing_parents:
                        existing.parents.append(DatabaseSample.get(parent.uid))
                existing_children = {child.identifier for child in existing.children}
                for child in model.children:
                    if child.identifier not in existing_children:
                        existing.children.append(DatabaseSample.get(child.uid))
                existing_images = {image.identifier for image in existing.images}
                for image in model.images:
                    if image.identifier not in existing_images:
                        existing.images.append(DatabaseImage.get(image.uid))
                existing_observations = {
                    observation.identifier for observation in existing.observations
                }
                for observation in model.observations:
                    if observation.identifier not in existing_observations:
                        existing.observations.append(
                            DatabaseObservation.get(observation.uid)
                        )

            return existing
        if model.parents is not None:
            parents = (DatabaseSample.get(sample.uid) for sample in model.parents)
        else:
            parents = None
        if model.children is not None:
            children = (DatabaseSample.get(sample.uid) for sample in model.children)
        else:
            children = None

        attributes = {
            tag: DatabaseAttribute.from_model(attribute)
            for tag, attribute in model.attributes.items()
        }
        return cls(
            project=DatabaseProject.get(model.project_uid),
            schema=DatabaseSampleSchema.get(model.schema_uid),
            identifier=model.identifier,
            parents=parents,
            children=children,
            attributes=attributes,
            name=model.name,
            pseudonym=model.pseudonym,
            selected=model.selected,
            uid=model.uid,
        )

    @property
    def model(self) -> Sample:
        return Sample(
            uid=self.uid,
            identifier=self.identifier,
            name=self.name,
            pseudonym=self.pseudonym,
            selected=self.selected,
            valid=self.valid_attributes and self.valid_relations,
            valid_attributes=self.valid_attributes,
            valid_relations=self.valid_relations,
            attributes={
                key: attribute.model for key, attribute in self.attributes.items()
            },
            project_uid=self.project.uid,
            schema_display_name=self.schema.display_name,
            schema_uid=self.schema.uid,
            children=[child.reference for child in self.children],
            parents=[parent.reference for parent in self.parents],
            images=[image.reference for image in self.images],
            observations=[observation.reference for observation in self.observations],
        )

    def get_children_of_type(
        self,
        sample_schema: Union[UUID, DatabaseSampleSchema],
        recursive: bool = False,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> Set["DatabaseSample"]:
        if self.children is None:
            return set()
        if isinstance(sample_schema, DatabaseSampleSchema):
            sample_schema = sample_schema.uid
        children = set(
            [
                child
                for child in self.children
                if child.schema_uid == sample_schema
                and (selected is None or child.selected == selected)
                and (valid is None or child.valid == valid)
            ]
        )
        if recursive:
            for child in self.children:
                children.update(
                    child.get_children_of_type(sample_schema, True, selected, valid)
                )
        return children

    def get_parents_of_type(
        self,
        sample_schema: Union[UUID, DatabaseSampleSchema],
        recursive: bool = False,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> Set["DatabaseSample"]:
        if self.parents is None:
            return set()
        if isinstance(sample_schema, DatabaseSampleSchema):
            sample_schema = sample_schema.uid
        parents = set(
            [
                parent
                for parent in self.parents
                if parent.schema_uid == sample_schema
                and (selected is None or parent.selected == selected)
                and (valid is None or parent.valid == valid)
            ]
        )
        if recursive:
            for parent in self.parents:
                parents.update(
                    parent.get_parents_of_type(sample_schema, True, selected, valid)
                )
        return parents

    def get_images_of_type(
        self,
        image_schema: Union[UUID, DatabaseImageSchema],
        recursive: bool = False,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> Set[DatabaseImage]:
        if self.images is None:
            return set()
        if isinstance(image_schema, DatabaseImageSchema):
            image_schema = image_schema.uid
        images = set(
            [
                image
                for image in self.images
                if image.schema_uid == image_schema
                and (selected is None or image.selected == selected)
                and (valid is None or image.valid == valid)
            ]
        )
        if recursive:
            for parent in self.parents:
                images.update(
                    parent.get_images_of_type(image_schema, True, selected, valid)
                )
        return images

    def get_child(
        self, identifier: str, schema: Union[UUID, DatabaseSampleSchema]
    ) -> Optional["DatabaseSample"]:
        return next(
            (
                child
                for child in self.get_children_of_type(schema)
                if child.identifier == identifier
            ),
            None,
        )

    @classmethod
    def get_or_add_child(
        cls,
        identifier: str,
        schema: Union[UUID, DatabaseSampleSchema],
        parents: Sequence["DatabaseSample"],
        attributes: Optional[Dict[str, DatabaseAttribute]] = None,
        name: Optional[str] = None,
        pseudonym: Optional[str] = None,
        commit: bool = True,
    ) -> "DatabaseSample":
        # Check if any of the parents already have the child
        child = next(
            (
                child
                for child in (
                    parent.get_child(identifier, schema) for parent in parents
                )
                if child is not None
            ),
            None,
        )

        if child is not None:
            # Add all parents to child
            child.set_parents(parents, commit=False)
        else:
            if not isinstance(schema, DatabaseSampleSchema):
                child_type_schema = DatabaseSampleSchema.get(schema)
                if child_type_schema is None:
                    raise ValueError(f"Sample schema with uid {schema} not found.")
                schema = child_type_schema
            # Create a new child
            child = cls(
                project=parents[0].project,
                name=name,
                schema=schema,
                parents=parents,
                attributes=attributes,
                identifier=identifier,
                pseudonym=pseudonym,
                commit=commit,
            )
        return child

    def get_image(self, identifier: str) -> Optional[DatabaseImage]:
        return next(
            (image for image in self.images if image.identifier == identifier), None
        )

    def get_images(self, recursive: bool = False) -> List[DatabaseImage]:
        images = self.images
        if recursive:
            images.extend(
                [image for child in self.children for image in child.get_images(True)]
            )
        return images

    def select(self, value: bool):
        self.selected = value
        [child.select_from_parent(self.selected) for child in self.children]
        [parent.select_from_child(self.selected) for parent in self.parents]
        [image.select(self.selected) for image in self.images]
        [observation.select(self.selected) for observation in self.observations]

    def select_from_parent(self, value: bool):
        if value:
            if all(parent.selected for parent in self.parents):
                self.selected = True
        else:
            self.selected = False
        [
            child.select_from_parent(self.selected)
            for child in self.children
            if child is not None
        ]
        [image.select_from_sample(self.selected) for image in self.images]
        [
            observation.select_from_sample(self.selected)
            for observation in self.observations
        ]

    def select_from_child(self, value: bool, selection_from: Optional[UUID] = None):
        if value:
            self.selected = True
        elif all(not child.selected for child in self.children):
            self.selected = False
        [
            parent.select_from_child(self.selected, self.uid)
            for parent in self.parents
            if parent is not None
        ]
        [image.select_from_sample(self.selected) for image in self.images]
        [
            observation.select_from_sample(self.selected)
            for observation in self.observations
            if not observation.uid == selection_from
        ]

    def set_parents(self, parents: Iterable[DatabaseSample], commit: bool = True):
        self.parents = list(parents)
        # self.validate(attributes=False)
        # for parent in self.parents:
        #     parent.validate(attributes=False)
        if commit:
            db.session.commit()

    def append_parents(self, parents: Iterable[DatabaseSample], commit: bool = True):
        self.parents.extend(parents)
        # self.validate(attributes=False)
        # for parent in parents:
        #     parent.validate(attributes=False)
        if commit:
            db.session.commit()

    def set_children(self, children: Iterable[DatabaseSample], commit: bool = True):
        self.children = list(children)
        # self.validate(attributes=False)
        # for child in self.children:
        #     child.validate(attributes=False)
        if commit:
            db.session.commit()

    def append_children(self, children: Iterable[DatabaseSample], commit: bool = True):
        self.children.extend(children)
        # self.validate(attributes=False)
        # for child in children:
        #     child.validate(attributes=False)
        if commit:
            db.session.commit()

    def set_images(self, images: Iterable[DatabaseImage], commit: bool = True):
        self.images = list(images)
        # self.validate(attributes=False)
        # for image in self.images:
        #     image.validate(attributes=False)
        if commit:
            db.session.commit()

    def set_observations(
        self, observations: Iterable[DatabaseObservation], commit: bool = True
    ):
        self.observations = list(observations)
        # self.validate(attributes=False)
        # for observation in self.observations:
        #     observation.validate(attributes=False)
        if commit:
            db.session.commit()

    def copy(self) -> DatabaseSample:
        return DatabaseSample(
            project=self.project,
            identifier=f"{self.identifier} (copy)",
            schema=self.schema,
            parents=self.parents,
            attributes={
                attribute.tag: attribute.copy()
                for attribute in self.attributes.values()
            },
            name=f"{self.name} (copy)" if self.name else None,
            pseudonym=f"{self.pseudonym} (copy)" if self.pseudonym else None,
            add=False,
            commit=False,
        )
