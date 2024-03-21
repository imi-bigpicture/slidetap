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

from flask import current_app
from sqlalchemy import Select, Uuid, and_, func, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm.collections import attribute_mapped_collection

from slidetap.database.attribute import Attribute
from slidetap.database.db import DbBase, NotAllowedActionError, db
from slidetap.database.schema import (
    AnnotationSchema,
    ImageSchema,
    ItemSchema,
    ItemValueType,
    ObservationSchema,
    SampleSchema,
    Schema,
)
from slidetap.database.schema.attribute_schema import AttributeSchema
from slidetap.database.schema.project_schema import ProjectSchema
from slidetap.model.image_status import ImageStatus
from slidetap.model.project_item import ProjectItem
from slidetap.model.project_status import ProjectStatus
from slidetap.model.table import ColumnSort

ItemType = TypeVar("ItemType", bound="Item")


class Item(DbBase):
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
    attributes: Mapped[Dict[str, Attribute[Any, Any]]] = db.relationship(
        Attribute,
        collection_class=attribute_mapped_collection("tag"),
        cascade="all, delete-orphan",
    )  # type: ignore
    project: Mapped[Project] = db.relationship("Project")  # type: ignore

    # For relations
    schema_uid: Mapped[UUID] = db.Column(Uuid)
    project_uid: Mapped[UUID] = db.Column(Uuid, db.ForeignKey("project.uid"))

    # From relations
    __table_args__ = (db.ForeignKeyConstraint([schema_uid], [ItemSchema.uid]),)
    __mapper_args__ = {
        "polymorphic_on": "item_value_type",
    }

    def __init__(
        self,
        project: Project,
        schema: ItemSchema,
        identifier: str,
        name: Optional[str],
        pseudonym: Optional[str],
        attributes: Optional[Union[Sequence[Attribute], Dict[str, Attribute]]],
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
        elif not isinstance(attributes, dict):
            attributes = {
                attribute.tag: attribute
                for attribute in attributes
                if attribute is not None
            }
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

        self.valid_attributes = self._validate_attributes()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.uid} {self.schema.name}  {self.identifier}>"

    @hybrid_property
    @abstractmethod
    def schema(self) -> ItemSchema:
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

    @property
    def display_in_table_attributes(self) -> Dict[str, Attribute]:
        """Return only attributes that should be displayed in table."""
        return {
            attribute.tag: attribute
            for attribute in db.session.scalars(
                select(Attribute)
                .filter_by(item_uid=self.uid)
                .where(Attribute.schema.has(AttributeSchema.display_in_table))
            )
        }

    def commit(self):
        db.session.commit()

    def set_select(self, value: bool, commit: bool = True):
        self.select(value)
        if commit:
            db.session.commit()

    def set_attributes(
        self, attributes: Dict[str, Attribute], commit: bool = True
    ) -> None:
        self.attributes = attributes
        self.validate(relations=False)
        if commit:
            db.session.commit()

    def update_attributes(
        self, attributes: Dict[str, Attribute], commit: bool = True
    ) -> None:
        self.attributes.update(attributes)
        self.validate(attributes=True)
        if commit:
            db.session.commit()

    def set_name(self, name: str, commit: bool = True) -> None:
        self.name = name
        if commit:
            db.session.commit()

    def set_identifier(self, identifier: str, commit: bool = True) -> None:
        self.identifier = identifier
        if commit:
            db.session.commit()

    def validate(self, relations: bool = True, attributes: bool = True) -> bool:
        if relations:
            self.valid_relations = self._validate_relations()
        if attributes:
            self.valid_attributes = self._validate_attributes()
        return self.valid

    @abstractmethod
    def select(self, value: bool):
        """Should select or de-select the item."""
        raise NotImplementedError()

    @abstractmethod
    def copy(self) -> Item:
        """Should copy the item."""
        raise NotImplementedError()

    @abstractmethod
    def _validate_relations(self) -> bool:
        """Should return True if the item (excluding attributes) are valid."""
        raise NotImplementedError()

    def _validate_attributes(self, re_validate: bool = False) -> bool:
        if re_validate:
            return all(
                attribute.validate(False) for attribute in self.attributes.values()
            )
        return all(attribute.valid for attribute in self.attributes.values())

    def recursive_get_all_attributes(self, schema_uid: UUID) -> Set["Attribute"]:
        attributes: Set[Attribute] = set()
        for attribute in self.attributes.values():
            attributes.update(attribute.recursive_get_all_attributes(schema_uid))
        return attributes

    @classmethod
    def add(cls, item: Item):
        if item.uid is not None:
            raise ValueError("Item already added.")
        item.uid = uuid4()
        db.session.add(item)
        db.session.commit()

    @classmethod
    def get(cls: Type[ItemType], uid: UUID) -> ItemType:
        """Return item by id."""
        item = cls.get_optional(uid)
        if item is None:
            raise ValueError(f"Item with uid {uid} not found.")
        return item

    @classmethod
    def get_optional(cls: Type[ItemType], uid: UUID) -> Optional[ItemType]:
        """Return item by id."""
        return db.session.get(cls, uid)

    @classmethod
    def delete_for_project(
        cls, project: Union[UUID, "Project"], only_non_selected=False
    ):
        if not isinstance(project, Project):
            found_project = Project.get(project)
            if found_project is None:
                raise ValueError(f"Project with uid {project} not found.")
            project = found_project
        for item_schema in project.item_schemas:
            # Delete items per schema with commit to avoid trying to delete already
            # deleted orphans.
            items = cls.get_for_project(project, item_schema)
            for item in items:
                if only_non_selected and item.selected or item in db.session.deleted:
                    continue
                db.session.delete(item)

            db.session.commit()

    @classmethod
    def get_for_project(
        cls: Type[ItemType],
        project: Union[UUID, "Project"],
        schema: Optional[Union[UUID, ItemSchema]] = None,
        start: Optional[int] = None,
        size: Optional[int] = None,
        identifier_filter: Optional[str] = None,
        attributes_filters: Optional[Dict[str, str]] = None,
        sorting: Optional[Iterable[ColumnSort]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> Iterable[ItemType]:
        if isinstance(project, Project):
            project = project.uid
        if isinstance(schema, ItemSchema):
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
                        sort_by = Item.identifier
                    elif sort.column == "valid":
                        sort_by = Item.valid
                    else:
                        raise NotImplementedError(f"Got unknown column {sort.column}.")
                    if sort.descending:
                        sort_by = sort_by.desc()
                    query = query.order_by(sort_by)
                else:
                    sort_by = Attribute.display_value
                    if sort.descending:
                        sort_by = sort_by.desc()
                    query = (
                        query.join(Attribute)
                        .where(Attribute.schema.has(tag=sort.column))
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
        project: Union[UUID, "Project"],
        schema: Optional[Union[UUID, ItemSchema]] = None,
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

    def get_attribute(self, key: str) -> Attribute[Any, Any]:
        return self.attributes[key]

    @classmethod
    def _query_for_schema(
        cls,
        query: Select,
        project: Union[UUID, "Project"],
        schema: Optional[Union[UUID, ItemSchema]] = None,
        identifier_filter: Optional[str] = None,
        attributes_filters: Optional[Dict[str, str]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> Select:
        if isinstance(project, Project):
            project = project.uid
        if isinstance(schema, ItemSchema):
            schema = schema.uid
        query = query.filter_by(project_uid=project)
        if schema is not None:
            query = query.filter_by(schema_uid=schema)
        if identifier_filter is not None:
            query = query.filter(Item.identifier.icontains(identifier_filter))
        if attributes_filters is not None:
            for tag, value in attributes_filters.items():
                query = query.filter(
                    Item.attributes.any(
                        and_(
                            Attribute.display_value.icontains(value),
                            Attribute.schema.has(tag=tag),
                        )
                    )
                )
        if selected is not None:
            query = query.filter_by(selected=selected)
        if valid is not None:
            query = query.filter_by(valid=valid)
        return query


class Observation(Item):
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
    schema: Mapped[ObservationSchema] = db.relationship(ObservationSchema)  # type: ignore
    image: Mapped[Optional[Image]] = db.relationship(
        "Image", back_populates="observations", foreign_keys=[image_uid]
    )  # type: ignore
    sample: Mapped[Optional[Sample]] = db.relationship(
        "Sample", back_populates="observations", foreign_keys=[sample_uid]
    )  # type: ignore
    annotation: Mapped[Optional[Annotation]] = db.relationship(
        "Annotation", back_populates="observations", foreign_keys=[annotation_uid]
    )  # type: ignore

    # From relations

    __mapper_args__ = {
        "polymorphic_identity": ItemValueType.OBSERVATION,
    }

    def __init__(
        self,
        project: Project,
        schema: ObservationSchema,
        identifier: str,
        item: Optional[Union["Sample", "Image", "Annotation"]],
        attributes: Optional[Sequence[Attribute]] = None,
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

    @hybrid_property
    def item(self) -> Union["Image", "Sample", "Annotation"]:
        """Return the item the observation is related to, either an image or
        a sample."""
        if self.image is not None:
            return self.image
        if self.sample is not None:
            return self.sample
        raise ValueError("Image or sample should be set.")

    def _validate_relations(self) -> bool:
        return self.item is not None

    def set_item(
        self, item: Union["Image", "Sample", "Annotation"], commit: bool = True
    ) -> None:
        if isinstance(item, Image):
            self.image = item
        elif isinstance(item, Sample):
            self.sample = item
        elif isinstance(item, Annotation):
            self.annotation = item
        else:
            raise ValueError("Item should be an image, sample or annotation.")
        self.validate(attributes=False)
        item.validate(attributes=False)
        if commit:
            db.session.commit()

    def select(self, value: bool):
        self.selected = value
        if isinstance(self.item, Sample):
            self.item.select_from_child(value)
        else:
            self.item.select(value)

    def select_from_sample(self, value: bool):
        self.selected = value

    def copy(self) -> Observation:
        return Observation(
            project=self.project,
            schema=self.schema,
            identifier=f"{self.identifier} (copy)",
            item=self.item,
            attributes=[attribute.copy() for attribute in self.attributes.values()],
            name=f"{self.name} (copy)" if self.name else None,
            pseudonym=f"{self.pseudonym} (copy)" if self.pseudonym else None,
            add=False,
            commit=False,
        )


class Annotation(Item):
    """An annotation item. Is related to an image."""

    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("item.uid", ondelete="CASCADE"), primary_key=True
    )

    # For relations
    image_uid: Mapped[UUID] = mapped_column(db.ForeignKey("image.uid"))

    # Relationships
    schema: Mapped[AnnotationSchema] = db.relationship(AnnotationSchema)  # type: ignore
    image: Mapped[Optional[Image]] = db.relationship(
        "Image", back_populates="annotations", foreign_keys=[image_uid]
    )  # type: ignore
    observations: Mapped[List[Observation]] = db.relationship(
        "Observation",
        back_populates="annotation",
        foreign_keys=[Observation.annotation_uid],
    )  # type: ignore

    __mapper_args__ = {
        "polymorphic_identity": ItemValueType.ANNOTATION,
    }

    def __init__(
        self,
        project: Project,
        schema: AnnotationSchema,
        identifier: str,
        image: Optional[Image] = None,
        attributes: Optional[Sequence[Attribute]] = None,
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

    def set_image(self, image: Image, commit: bool = True):
        self.image = image
        self.validate(attributes=False)
        image.validate(attributes=False)
        if commit:
            db.session.commit()

    def copy(self) -> Item:
        return Annotation(
            project=self.project,
            schema=self.schema,
            identifier=f"{self.identifier} (copy)",
            image=self.image,
            attributes=[attribute.copy() for attribute in self.attributes.values()],
            name=f"{self.name} (copy)" if self.name else None,
            pseudonym=f"{self.pseudonym} (copy)" if self.pseudonym else None,
            add=False,
            commit=False,
        )

    def _validate_relations(self) -> bool:
        return self.image is not None


class ImageFile(DbBase):
    """Represents a file stored for an image."""

    uid: Mapped[UUID] = db.Column(Uuid, primary_key=True, default=uuid4)
    filename: Mapped[str] = db.Column(db.String(512))

    # For relations
    # TODO should optional be allowed here?
    image_uid: Mapped[Optional[UUID]] = mapped_column(db.ForeignKey("image.uid"))

    # Relations
    image: Mapped[Optional[Image]] = db.relationship(
        "Image",
        back_populates="files",
        foreign_keys=[image_uid],
    )  # type: ignore

    def __init__(self, filename: str, add: bool = True, commit: bool = True):
        """A file stored for a image.

        Parameters
        ----------
        filename: Name of file relative to image folder.

        """
        super().__init__(filename=filename, add=add, commit=commit)


class Image(Item):
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
    schema: Mapped[ImageSchema] = db.relationship(ImageSchema)  # type: ignore
    samples: Mapped[List[Sample]] = db.relationship(
        "Sample", secondary=sample_to_image, back_populates="images"
    )  # type: ignore
    annotations: Mapped[List[Annotation]] = db.relationship(
        Annotation,
        back_populates="image",
        foreign_keys=[Annotation.image_uid],
    )  # type: ignore
    observations: Mapped[List[Observation]] = db.relationship(
        Observation,
        back_populates="image",
        foreign_keys=[Observation.image_uid],
    )  # type: ignore
    files: Mapped[List[ImageFile]] = db.relationship(
        ImageFile,
        back_populates="image",
        foreign_keys=[ImageFile.image_uid],
        cascade="all, delete-orphan",
    )  # type: ignore

    __mapper_args__ = {
        "polymorphic_identity": ItemValueType.IMAGE,
    }

    def __init__(
        self,
        project: Project,
        schema: ImageSchema,
        identifier: str,
        samples: Union["Sample", Sequence["Sample"]],
        attributes: Optional[Sequence[Attribute]] = None,
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
            if not isinstance(samples, Sequence):
                samples = [samples]
            self.set_samples(samples, commit=False)
        if commit:
            db.session.commit()

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

    def _validate_relations(self) -> bool:
        if self.failed:
            return False
        return len(self.samples) > 0

    def set_as_downloading(self):
        if not self.not_started:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.NOT_STARTED} image as "
                f"{ImageStatus.DOWNLOADING}, was {self.status}."
            )
        self.status = ImageStatus.DOWNLOADING
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

    def set_as_pre_processed(self):
        if not self.pre_processing:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.PRE_PROCESSING} image as "
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
        if value:
            if all(parent.selected for parent in self.samples):
                self.selected = True
        else:
            self.selected = False

    @classmethod
    def get_or_add(
        cls,
        identifier: str,
        schema: ImageSchema,
        samples: Sequence["Sample"],
        attributes: Optional[Sequence[Attribute]] = None,
        name: Optional[str] = None,
        pseudonym: Optional[str] = None,
        external_identifier: Optional[str] = None,
        commit: bool = True,
    ) -> "Image":
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

    def set_folder_path(self, path: Path):
        self.folder_path = str(path)
        db.session.commit()

    def set_thumbnail_path(self, path: Path):
        self.thumbnail_path = str(path)
        db.session.commit()

    def set_files(self, files: List[ImageFile]):
        self.files = files
        db.session.commit()

    def set_samples(self, samples: Iterable[Sample], commit: bool = True):
        self.samples = list(samples)
        self.validate(attributes=False)
        for sample in self.samples:
            sample.validate(attributes=False)
        if commit:
            db.session.commit()

    @classmethod
    def get_images_with_thumbnails(cls, project: Project) -> Iterable["Image"]:
        """Return image id with thumbnail."""
        return db.session.scalars(
            select(Image).filter(
                cls.project_uid == project.uid, cls.thumbnail_path.isnot(None)
            )
        )

    def copy(self) -> Image:
        return Image(
            project=self.project,
            schema=self.schema,
            identifier=f"{self.identifier} (copy)",
            samples=self.samples,
            attributes=[attribute.copy() for attribute in self.attributes.values()],
            name=f"{self.name} (copy)" if self.name else None,
            pseudonym=f"{self.pseudonym} (copy)" if self.pseudonym else None,
            add=False,
            commit=False,
        )


class Sample(Item):
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
    children: Mapped[List[Sample]] = db.relationship(
        "Sample",
        secondary=sample_to_sample,
        primaryjoin=(uid == sample_to_sample.c.parent_uid),
        secondaryjoin=(uid == sample_to_sample.c.child_uid),
        back_populates="parents",
        cascade="all, delete",
    )  # type: ignore
    parents: Mapped[List[Sample]] = db.relationship(
        "Sample",
        secondary=sample_to_sample,
        primaryjoin=(uid == sample_to_sample.c.child_uid),
        secondaryjoin=(uid == sample_to_sample.c.parent_uid),
        back_populates="children",
    )  # type: ignore
    images: Mapped[List[Image]] = db.relationship(
        Image, secondary=Image.sample_to_image, back_populates="samples"
    )  # type: ignore
    observations: Mapped[List[Observation]] = db.relationship(
        Observation,
        back_populates="sample",
        foreign_keys=[Observation.sample_uid],
    )  # type: ignore

    schema: Mapped[SampleSchema] = db.relationship(SampleSchema)  # type: ignore

    __mapper_args__ = {
        "polymorphic_identity": ItemValueType.SAMPLE,
    }

    def __init__(
        self,
        project: Project,
        schema: SampleSchema,
        identifier: str,
        parents: Optional[Union["Sample", Sequence["Sample"]]] = None,
        attributes: Optional[Sequence[Attribute]] = None,
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
            if not isinstance(parents, Sequence):
                parents = [parents]
            self.set_parents(parents, commit=False)
        if commit:
            db.session.commit()

    def _validate_relations(self) -> bool:
        for relation in self.schema.children:
            children_of_type = self.get_children_of_type(relation.child)
            if (
                relation.min_children is not None
                and len(children_of_type) < relation.min_children
            ) or (
                relation.max_children is not None
                and len(children_of_type) > relation.max_children
            ):
                return False

        for relation in self.schema.parents:
            parents_of_type = self.get_parents_of_type(relation.parent)
            if (
                relation.min_parents is not None
                and len(parents_of_type) < relation.min_parents
            ) or (
                relation.max_parents is not None
                and len(parents_of_type) > relation.max_parents
            ):
                return False
        return True

    def get_children_of_type(
        self, sample_schema: Union[UUID, SampleSchema], recursive: bool = False
    ) -> Set["Sample"]:
        if isinstance(sample_schema, SampleSchema):
            sample_schema = sample_schema.uid
        children = set(
            [child for child in self.children if child.schema.uid == sample_schema]
        )
        if recursive:
            for child in self.children:
                children.update(child.get_children_of_type(sample_schema, True))
        return children

    def get_parents_of_type(
        self, sample_schema: Union[UUID, SampleSchema], recursive: bool = False
    ) -> Set["Sample"]:
        if isinstance(sample_schema, SampleSchema):
            sample_schema = sample_schema.uid
        parents = set(
            [parent for parent in self.parents if parent.schema.uid == sample_schema]
        )
        if recursive:
            for parent in self.parents:
                parents.update(parent.get_parents_of_type(sample_schema, True))
        return parents

    def get_child(
        self, identifier: str, schema: Union[UUID, SampleSchema]
    ) -> Optional["Sample"]:
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
        schema: Union[UUID, SampleSchema],
        parents: Sequence["Sample"],
        attributes: Optional[Sequence[Attribute]] = None,
        name: Optional[str] = None,
        pseudonym: Optional[str] = None,
        commit: bool = True,
    ) -> "Sample":
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
            if not isinstance(schema, SampleSchema):
                child_type_schema = SampleSchema.get_by_uid(schema)
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

    def get_image(self, identifier: str) -> Optional[Image]:
        return next(
            (image for image in self.images if image.identifier == identifier), None
        )

    def get_images(self, recursive: bool = False) -> List[Image]:
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

    def select_from_child(self, value: bool):
        if value:
            self.selected = True
        else:
            if all(not child.selected for child in self.children):
                self.selected = False
        [
            parent.select_from_child(self.selected)
            for parent in self.parents
            if parent is not None
        ]
        [image.select_from_sample(self.selected) for image in self.images]
        [
            observation.select_from_sample(self.selected)
            for observation in self.observations
        ]

    def set_parents(self, parents: Iterable[Sample], commit: bool = True):
        self.parents = list(parents)
        self.validate(attributes=False)
        for parent in self.parents:
            parent.validate(attributes=False)
        if commit:
            db.session.commit()

    def append_parents(self, parents: Iterable[Sample], commit: bool = True):
        self.parents.extend(parents)
        self.validate(attributes=False)
        for parent in parents:
            parent.validate(attributes=False)
        if commit:
            db.session.commit()

    def set_children(self, children: Iterable[Sample], commit: bool = True):
        self.children = list(children)
        self.validate(attributes=False)
        for child in self.children:
            child.validate(attributes=False)
        if commit:
            db.session.commit()

    def append_children(self, children: Iterable[Sample], commit: bool = True):
        self.children.extend(children)
        self.validate(attributes=False)
        for child in children:
            child.validate(attributes=False)
        if commit:
            db.session.commit()

    def copy(self) -> Sample:
        return Sample(
            project=self.project,
            identifier=f"{self.identifier} (copy)",
            schema=self.schema,
            parents=self.parents,
            attributes=[attribute.copy() for attribute in self.attributes.values()],
            name=f"{self.name} (copy)" if self.name else None,
            pseudonym=f"{self.pseudonym} (copy)" if self.pseudonym else None,
            add=False,
            commit=False,
        )


class Project(DbBase):
    """Represents a project containing samples, images, annotations, and
    observations."""

    uid: Mapped[UUID] = db.Column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = db.Column(db.String(128))
    status: Mapped[ProjectStatus] = db.Column(db.Enum(ProjectStatus))
    valid_attributes: Mapped[bool] = db.Column(db.Boolean)

    # Relations
    schema: Mapped[ProjectSchema] = db.relationship(ProjectSchema)  # type: ignore
    root_schema: Mapped[Schema] = db.relationship(Schema)  # type: ignore
    # Relations
    attributes: Mapped[Dict[str, Attribute[Any, Any]]] = db.relationship(
        Attribute,
        collection_class=attribute_mapped_collection("tag"),
        cascade="all, delete-orphan",
    )  # type: ignore

    # For relations
    schema_uid: Mapped[UUID] = db.Column(Uuid, db.ForeignKey("schema.uid"))
    project_schema_uid: Mapped[UUID] = db.Column(
        Uuid, db.ForeignKey("project_schema.uid")
    )

    def __init__(
        self,
        name: str,
        schema: ProjectSchema,
        attributes: Optional[Union[Sequence[Attribute], Dict[str, Attribute]]] = None,
        add: bool = True,
        commit: bool = True,
    ):
        """Create a project.

        Parameters
        ----------
        name: str
            Name of project.

        """
        if attributes is None:
            attributes = {}
        elif not isinstance(attributes, dict):
            attributes = {
                attribute.tag: attribute
                for attribute in attributes
                if attribute is not None
            }
        else:
            attributes = {
                attribute.tag: attribute
                for attribute in attributes.values()
                if attribute is not None
            }
        super().__init__(
            name=name,
            schema=schema,
            root_schema=schema.schema,
            attributes=attributes,
            status=ProjectStatus.INITIALIZED,
            add=add,
            commit=commit,
        )

    def __str__(self) -> str:
        return f"Project id: {self.uid}, name {self.name}, " f"status: {self.status}."

    @hybrid_property
    def initialized(self) -> bool:
        """Return True if project have status 'INITIALIZED'."""
        return self.status == ProjectStatus.INITIALIZED

    @hybrid_property
    def metadata_searching(self) -> bool:
        """Return True if project have status 'METADATA_SEARCHING'."""
        return self.status == ProjectStatus.METADATA_SEARCHING

    @hybrid_property
    def metadata_search_complete(self) -> bool:
        """Return True if project have status 'SEARCH_COMPLETE'."""
        return self.status == ProjectStatus.METADATA_SEARCH_COMPLETE

    @hybrid_property
    def image_pre_processing(self) -> bool:
        """Return True if project have status 'IMAGE_PRE_PROCESSING'."""
        return self.status == ProjectStatus.IMAGE_PRE_PROCESSING

    @hybrid_property
    def image_pre_processing_complete(self) -> bool:
        """Return True if project have status 'IMAGE_PRE_PROCESSING_COMPLETE'."""
        return self.status == ProjectStatus.IMAGE_PRE_PROCESSING_COMPLETE

    @hybrid_property
    def image_post_processing(self) -> bool:
        """Return True if project have status 'IMAGE_POST_PROCESSING'."""
        return self.status == ProjectStatus.IMAGE_POST_PROCESSING

    @hybrid_property
    def image_post_processing_complete(self) -> bool:
        """Return True if project have status 'IMAGE_POST_PROCESSING_COMPLETE'."""
        return self.status == ProjectStatus.IMAGE_POST_PROCESSING_COMPLETE

    @hybrid_property
    def exporting(self) -> bool:
        """Return True if project have status 'EXPORTING'."""
        return self.status == ProjectStatus.EXPORTING

    @hybrid_property
    def export_complete(self) -> bool:
        """Return True if project have status 'EXPORT_COMPLETE'."""
        return self.status == ProjectStatus.EXPORT_COMPLETE

    @hybrid_property
    def failed(self) -> bool:
        """Return True if project have status 'FAILED'."""
        return self.status == ProjectStatus.FAILED

    @hybrid_property
    def deleted(self) -> bool:
        return self.status == ProjectStatus.DELETED

    @property
    def items(self) -> Sequence[ProjectItem]:
        return [
            ProjectItem(
                schema=item_schema,
                count=Item.get_count_for_project(
                    self.uid, item_schema.uid, selected=True
                ),
            )
            for item_schema in ItemSchema.get_for_schema(self.root_schema.uid)
        ]

    @property
    def item_schemas(self) -> Iterable[ItemSchema]:
        return ItemSchema.get_for_schema(self.root_schema.uid)

    @property
    def item_counts(self) -> List[int]:
        return [
            Item.get_count_for_project(self.uid, item_schema.uid, selected=True)
            for item_schema in ItemSchema.get_for_schema(self.root_schema.uid)
        ]

    @property
    def valid(self) -> bool:
        if not self.valid_attributes:
            current_app.logger.info(
                f"Project {self.uid} is not valid as attributes are not valid."
            )
            return False
        not_valid_item = next(
            (
                item
                for item in Item.get_for_project(self.uid, selected=True, valid=False)
            ),
            None,
        )
        if not_valid_item is None:
            return True
        current_app.logger.info(
            f"Project {self.uid} is not valid as item {not_valid_item} is not valid. "
            f"Status of item is attributes {not_valid_item.valid_attributes}, "
            f"{next((attribute for attribute in not_valid_item.attributes.values() if not attribute.valid), None)},"
            f"relations {not_valid_item.valid_relations}."
        )
        current_app.logger.info(
            f"{[(attribute, attribute.valid) for attribute in not_valid_item.attributes.values()]}"
        )
        return False

    @classmethod
    def get(cls, uid: UUID) -> Optional["Project"]:
        """Return project for id.

        Parameters
        ----------
        id: int
            Id of project to get.

        Returns
        ----------
        Optional[Project]
            Project, or None if not found.
        """
        return db.session.get(cls, uid)

    @classmethod
    def get_all_projects(cls) -> Iterable["Project"]:
        """Return all projects
        Returns
        ----------
        List[Project]
            List of projects.
        """
        return db.session.scalars(select(cls))

    def reset(self):
        """Reset status."""
        allowed_statuses = [
            ProjectStatus.INITIALIZED,
            ProjectStatus.METADATA_SEARCHING,
            ProjectStatus.METADATA_SEARCH_COMPLETE,
        ]
        if self.status not in allowed_statuses:
            raise NotAllowedActionError(
                f"Can only set {', '.join(status.name for status in allowed_statuses)} "
                f"project as {ProjectStatus.INITIALIZED}, was {self.status}"
            )
        self.status = ProjectStatus.INITIALIZED
        db.session.commit()

    def delete_project(self):
        """Delete project"""

        if (
            not self.initialized
            or self.metadata_searching
            or self.metadata_search_complete
        ):
            return
        self.status = ProjectStatus.DELETED
        db.session.delete(self)
        db.session.commit()

    def set_as_searching(self):
        """Set project as 'SEARCHING' if not started."""
        if not self.initialized:
            raise NotAllowedActionError(
                f"Can only set {ProjectStatus.INITIALIZED} project as "
                f"{ProjectStatus.METADATA_SEARCHING}, was {self.status}"
            )
        self.status = ProjectStatus.METADATA_SEARCHING
        current_app.logger.debug(f"Project {self.uid} set as searching.")
        db.session.commit()

    def set_as_search_complete(self):
        """Set project as 'SEARCH_COMPLETE' if not started."""
        if not self.metadata_searching:
            raise NotAllowedActionError(
                f"Can only set {ProjectStatus.METADATA_SEARCHING} project as "
                f"{ProjectStatus.METADATA_SEARCH_COMPLETE}, was {self.status}"
            )
        self.status = ProjectStatus.METADATA_SEARCH_COMPLETE
        current_app.logger.debug(f"Project {self.uid} set as search complete.")
        db.session.commit()

    def set_as_pre_processing(self):
        """Set project as 'PRE_PROCESSING' if not started."""
        if not self.metadata_search_complete:
            raise NotAllowedActionError(
                f"Can only set {ProjectStatus.METADATA_SEARCH_COMPLETE} project as "
                f"{ProjectStatus.IMAGE_PRE_PROCESSING}, was {self.status}"
            )
        self.status = ProjectStatus.IMAGE_PRE_PROCESSING
        current_app.logger.debug(f"Project {self.uid} set as pre-processing.")
        db.session.commit()

    def set_as_pre_processed(self):
        """Set project as 'PRE_PROCESSED' if not started."""
        if not self.image_pre_processing:
            raise NotAllowedActionError(
                f"Can only set {ProjectStatus.IMAGE_PRE_PROCESSING} project as "
                f"{ProjectStatus.IMAGE_PRE_PROCESSING_COMPLETE}, was {self.status}"
            )
        self.status = ProjectStatus.IMAGE_PRE_PROCESSING_COMPLETE
        current_app.logger.debug(f"Project {self.uid} set as pre-processed.")
        db.session.commit()

    def set_as_post_processing(self):
        """Set project as 'POST_PROCESSING' if not started."""
        if not self.image_pre_processing_complete:
            raise NotAllowedActionError(
                f"Can only set {ProjectStatus.IMAGE_PRE_PROCESSING_COMPLETE} project as "
                f"{ProjectStatus.IMAGE_POST_PROCESSING}, was {self.status}"
            )
        self.status = ProjectStatus.IMAGE_POST_PROCESSING
        current_app.logger.debug(f"Project {self.uid} set as post-processing.")
        db.session.commit()

    def set_as_post_processed(self):
        """Set project as 'POST_PROCESSED' if not started."""
        if not self.image_post_processing:
            raise NotAllowedActionError(
                f"Can only set {ProjectStatus.IMAGE_POST_PROCESSING} project as "
                f"{ProjectStatus.IMAGE_POST_PROCESSING_COMPLETE}, was {self.status}"
            )
        self.status = ProjectStatus.IMAGE_POST_PROCESSING_COMPLETE
        current_app.logger.debug(f"Project {self.uid} set as post-processed.")
        db.session.commit()

    def set_as_exporting(self):
        """Set project as 'EXPORTING' if not started."""
        if not self.image_post_processing_complete:
            raise NotAllowedActionError(
                f"Can only set {ProjectStatus.IMAGE_POST_PROCESSING_COMPLETE} project as "
                f"{ProjectStatus.EXPORTING}, was {self.status}"
            )
        self.status = ProjectStatus.EXPORTING
        current_app.logger.debug(f"Project {self.uid} set as exporting.")
        db.session.commit()

    def set_as_export_complete(self):
        """Set project as 'EXPORT_COMPLETE' if not started."""
        if not self.exporting:
            raise NotAllowedActionError(
                f"Can only set {ProjectStatus.EXPORTING} project as "
                f"{ProjectStatus.EXPORT_COMPLETE}, was {self.status}"
            )
        self.status = ProjectStatus.EXPORT_COMPLETE
        current_app.logger.debug(f"Project {self.uid} set as export complete.")
        db.session.commit()

    def set_as_failed(self):
        """Set status of project to 'FAILED'."""
        self.status = ProjectStatus.FAILED
        current_app.logger.debug(f"Project {self.uid} set as failed.")
        db.session.commit()

    def update(self):
        db.session.commit()

    def set_status_if_all_images_post_processed(self):
        if self.failed:
            return
        images_for_project = select(Image).filter_by(project_uid=self.uid)

        any_non_completed = db.session.scalars(
            images_for_project.filter(
                Image.status != ImageStatus.POST_PROCESSING_FAILED,
                Image.status != ImageStatus.POST_PROCESSED,
            )
        ).first()
        if any_non_completed is not None:
            current_app.logger.debug(
                f"Project {self.uid} not yet finished post-processing. "
                f"Image {any_non_completed} has status {any_non_completed.status}."
            )
            return
        current_app.logger.debug(f"Project {self.uid} post-processed.")
        self.set_as_post_processed()

    def set_status_if_all_images_pre_processed(self):
        if self.failed:
            return
        images_for_project = select(Image).filter_by(project_uid=self.uid)

        any_non_completed = db.session.scalars(
            images_for_project.filter(
                Image.status != ImageStatus.PRE_PROCESSING_FAILED,
                Image.status != ImageStatus.PRE_PROCESSED,
            )
        ).first()
        if any_non_completed is not None:
            current_app.logger.debug(
                f"Project {self.uid} not yet finished pre-processing. "
                f"Image {any_non_completed} has status {any_non_completed.status}."
            )
            return
        current_app.logger.debug(f"Project {self.uid} pre-processed.")
        self.set_as_pre_processed()

    def set_attributes(
        self, attributes: Dict[str, Attribute], commit: bool = True
    ) -> None:
        self.attributes = attributes
        self.valid_attributes = self._validate_attributes()
        if commit:
            db.session.commit()

    def update_attributes(
        self, attributes: Dict[str, Attribute], commit: bool = True
    ) -> None:
        self.attributes.update(attributes)
        self.valid_attributes = self._validate_attributes()
        if commit:
            db.session.commit()

    def _validate_attributes(self, re_validate: bool = False) -> bool:
        if re_validate:
            return all(
                attribute.validate(False) for attribute in self.attributes.values()
            )
        return all(attribute.valid for attribute in self.attributes.values())
