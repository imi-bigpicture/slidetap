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
from sqlalchemy import Uuid, func, select
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
from slidetap.model import ImageStatus, ProjectStatus
from slidetap.model.project_item import ProjectItem

ItemType = TypeVar("ItemType", bound="Item")


class Item(DbBase):
    """Base class for an metadata item."""

    uid: Mapped[UUID] = db.Column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = db.Column(db.String(128))
    selected: Mapped[bool] = db.Column(db.Boolean, default=True)
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
        name: str,
        attributes: Optional[Union[Sequence[Attribute], Dict[str, Attribute]]] = None,
        add: bool = True,
        commit: bool = True,
        uid: Optional[UUID] = None,
        **kwargs,
    ):
        """Create and add an item to the database.

        Parameters
        ----------
        project: Project
            Project the item belongs to.
        name: str
            The name of the item.
        attributes: Optional[Dict[str, Any]] = None
            Optional dictionary of attributes for the item.
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
            commit=commit,
            project=project,
            name=name,
            attributes=attributes,
            uid=uid,
            **kwargs,
        )

    @property
    def schema(self) -> ItemSchema:
        raise NotImplementedError()

    @property
    def schema_name(self) -> str:
        return self.schema.name

    @property
    def schema_display_name(self) -> str:
        return self.schema.display_name

    def set_select(self, value: bool, commit: bool = True):
        self.select(value)
        if commit:
            db.session.commit()

    def set_attributes(
        self, attributes: Dict[str, Attribute], commit: bool = True
    ) -> None:
        self.attributes = attributes
        if commit:
            db.session.commit()

    def set_name(self, name: str, commit: bool = True) -> None:
        self.name = name
        if commit:
            db.session.commit()

    @abstractmethod
    def select(self, value: bool):
        """Should select or de-select the item."""
        raise NotImplementedError()

    @abstractmethod
    def copy(self) -> Item:
        """Should copy the item."""
        raise NotImplementedError()

    @property
    @abstractmethod
    def is_valid(self) -> bool:
        """Should return True if the item and its attributes are valid."""
        raise NotImplementedError()

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
    def delete_for_project(cls, project_uid: UUID, only_non_selected=False):
        # Workaround as the commented out section does not delete the data in the
        # polymorphic tables.
        items = cls.get_for_project(project_uid)
        for item in items:
            if only_non_selected and item.selected:
                continue
            db.session.delete(item)
        # query = delete(cls).where(cls.project_uid == project_uid)
        # if only_non_selected:
        #     query = query.where(cls.selected.is_(False))
        # db.session.execute(query)
        db.session.commit()

    @classmethod
    def get_for_project(
        cls: Type[ItemType],
        project_uid: UUID,
        schema_uid: Optional[UUID] = None,
        selected: Optional[bool] = None,
    ) -> Sequence[ItemType]:
        query = select(cls).filter_by(project_uid=project_uid)
        if schema_uid is not None:
            query = query.filter_by(schema_uid=schema_uid)
        if selected is not None:
            query = query.filter_by(selected=selected)
        return db.session.scalars(query).all()

    @classmethod
    def get_count_for_project(
        cls,
        project_uid: UUID,
        schema_uid: Optional[UUID] = None,
        selected: Optional[bool] = None,
    ) -> int:
        query = select(func.count(cls.uid)).filter_by(project_uid=project_uid)

        if schema_uid is not None:
            query = query.filter_by(schema_uid=schema_uid)
        if selected is not None:
            query = query.filter_by(selected=selected)
        return db.session.scalars(query).one()

    def get_attribute(self, key: str) -> Attribute[Any, Any]:
        return self.attributes[key]

    def update_attributes(self, update: Dict[str, Attribute]) -> None:
        self.attributes.update(update)
        db.session.commit()


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
        name: str,
        observation_schema: ObservationSchema,
        item: Optional[Union["Sample", "Image", "Annotation"]],
        attributes: Optional[Sequence[Attribute]] = None,
        add: bool = True,
        commit: bool = True,
    ):
        kwargs = {}
        if isinstance(item, Sample):
            kwargs["sample"] = item
        elif isinstance(item, Image):
            kwargs["image"] = item
        elif isinstance(item, Annotation):
            kwargs["annotation"] = item
        super().__init__(
            name=name,
            project=project,
            attributes=attributes,
            schema=observation_schema,
            add=add,
            commit=commit,
            **kwargs,
        )

    @property
    def item(self) -> Union["Image", "Sample", "Annotation"]:
        """Return the item the observation is related to, either an image or
        a sample."""
        if self.image is not None:
            return self.image
        if self.sample is not None:
            return self.sample
        raise ValueError("Image or sample should be set.")

    @property
    def is_valid(self) -> bool:
        if self.item is None:
            return False

        all_attributes_valid = all(
            attribute.is_valid for attribute in self.attributes.values()
        )
        return all_attributes_valid

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
            self.project,
            f"{self.name} (copy)",
            self.schema,
            self.item,
            [attribute.copy() for attribute in self.attributes.values()],
            False,
            False,
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
        name: str,
        annotation_schema: AnnotationSchema,
        image: Optional[Image] = None,
        attributes: Optional[Sequence[Attribute]] = None,
        add: bool = True,
        commit: bool = True,
    ):
        kwargs = {}
        super().__init__(
            name=name,
            project=project,
            attributes=attributes,
            schema=annotation_schema,
            image=image,
            add=add,
            commit=commit,
            **kwargs,
        )

    def set_image(self, image: Image, commit: bool = True):
        self.image = image
        if commit:
            db.session.commit()

    def copy(self) -> Item:
        return Annotation(
            self.project,
            f"{self.name} (copy)",
            self.schema,
            self.image,
            [attribute.copy() for attribute in self.attributes.values()],
            False,
            False,
        )

    @property
    def is_valid(self) -> bool:
        if self.image is None:
            return False
        all_attributes_valid = all(
            attribute.is_valid for attribute in self.attributes.values()
        )
        return all_attributes_valid


class ImageFile(DbBase):
    """Represents a file stored for an image."""

    uid: Mapped[UUID] = db.Column(Uuid, primary_key=True, default=uuid4)
    filename: Mapped[str] = db.Column(db.String(512))

    # For relations
    # TODO should optional be allowed here?
    image_uid: Mapped[Optional[UUID]] = mapped_column(db.ForeignKey("image.uid"))

    # Relations
    image: Mapped[Image] = db.relationship(
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
    folder_path: Mapped[str] = db.Column(db.String(512))
    thumbnail_path: Mapped[str] = db.Column(db.String(512))

    status: Mapped[ImageStatus] = db.Column(db.Enum(ImageStatus))

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
    )  # type: ignore

    __mapper_args__ = {
        "polymorphic_identity": ItemValueType.IMAGE,
    }

    def __init__(
        self,
        project: Project,
        name: str,
        image_schema: ImageSchema,
        samples: Union["Sample", Sequence["Sample"]],
        attributes: Optional[Sequence[Attribute]] = None,
        add: bool = True,
        commit: bool = True,
    ):
        if not isinstance(samples, Sequence):
            samples = [samples]
        super().__init__(
            name=name,
            project=project,
            attributes=attributes,
            schema=image_schema,
            status=ImageStatus.NOT_STARTED,
            samples=list(samples),
            add=add,
            commit=commit,
        )

    @property
    def not_started(self) -> bool:
        return self.status == ImageStatus.NOT_STARTED

    @property
    def downloading(self) -> bool:
        return self.status == ImageStatus.DOWNLOADING

    @property
    def downloaded(self) -> bool:
        return self.status == ImageStatus.DOWNLOADED

    @property
    def pre_processing(self) -> bool:
        return self.status == ImageStatus.PRE_PROCESSING

    @property
    def pre_processed(self) -> bool:
        return self.status == ImageStatus.PRE_PROCESSED

    @property
    def post_processing(self) -> bool:
        return self.status == ImageStatus.POST_PROCESSING

    @property
    def post_processed(self) -> bool:
        return self.status == ImageStatus.POST_PROCESSED

    @property
    def failed(self) -> bool:
        return self.status == ImageStatus.FAILED

    @property
    def completed(self) -> bool:
        return self.status == ImageStatus.COMPLETED

    @property
    def is_valid(self) -> bool:
        if len(self.samples) == 0:
            return False
        all_attributes_valid = all(
            attribute.is_valid for attribute in self.attributes.values()
        )
        return all_attributes_valid

    def set_as_downloading(self):
        if not self.not_started:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.NOT_STARTED} image as "
                f"{ImageStatus.DOWNLOADING}, was {self.status}."
            )
        self.status = ImageStatus.DOWNLOADING
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

    def set_as_pre_processed(self):
        if not self.pre_processing:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.PRE_PROCESSING} image as "
                f"{ImageStatus.PRE_PROCESSED}, was {self.status}."
            )
        self.status = ImageStatus.PRE_PROCESSED
        db.session.commit()
        self.project.set_status_if_all_images_pre_processed()

    def set_as_post_processing(self):
        if not self.pre_processed:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.PRE_PROCESSED} image as "
                f"{ImageStatus.POST_PROCESSING}, was {self.status}."
            )
        self.status = ImageStatus.POST_PROCESSING
        db.session.commit()

    def set_as_post_processed(self):
        if not self.post_processing:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.POST_PROCESSING} image as "
                f"{ImageStatus.POST_PROCESSED}, was {self.status}."
            )
        self.status = ImageStatus.POST_PROCESSED
        db.session.commit()
        self.project.set_status_if_all_images_post_processed()

    def set_as_failed(self):
        self.status = ImageStatus.FAILED
        db.session.commit()

    def set_as_completed(self):
        if not self.post_processed:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.POST_PROCESSED} image as "
                f"{ImageStatus.COMPLETED}, was {self.status}."
            )
        self.status = ImageStatus.COMPLETED
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
        name: str,
        image_type: ImageSchema,
        samples: Sequence["Sample"],
        attributes: Optional[Sequence[Attribute]] = None,
        commit: bool = True,
    ) -> "Image":
        # Check if any of the samples already have the image
        image = next(
            (
                sample
                for sample in (sample.get_image(name) for sample in samples)
                if sample is not None
            ),
            None,
        )

        if image is not None:
            # Add all samples to image
            image.samples = list(samples)
        else:
            # Create a new image
            image = cls(
                samples[0].project,
                name,
                image_type,
                samples,
                attributes,
                commit,
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
        if commit:
            db.session.commit()

    @classmethod
    def get_images_with_thumbnails(cls, project: Project) -> Sequence["Image"]:
        """Return image id with thumbnail."""
        return db.session.scalars(
            select(Image).filter(
                cls.project_uid == project.uid, cls.thumbnail_path.isnot(None)
            )
        ).all()

    def copy(self) -> Image:
        return Image(
            self.project,
            f"{self.name} (copy)",
            self.schema,
            self.samples,
            [attribute.copy() for attribute in self.attributes.values()],
            False,
            False,
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
        name: str,
        sample_schema: SampleSchema,
        parents: Optional[Union["Sample", Sequence["Sample"]]] = None,
        attributes: Optional[Sequence[Attribute]] = None,
        add: bool = True,
        commit: bool = True,
        uid: Optional[UUID] = None,
    ):
        if parents is None:
            parents = []
        elif not isinstance(parents, Sequence):
            parents = [parents]

        super().__init__(
            name=name,
            project=project,
            attributes=attributes,
            schema=sample_schema,
            parents=list(parents),
            add=add,
            commit=commit,
            uid=uid,
        )

    @property
    def is_valid(self) -> bool:
        all_attributes_valid = all(
            attribute.is_valid for attribute in self.attributes.values()
        )
        return all_attributes_valid

    def get_children_of_type(self, sample_schema: SampleSchema) -> List["Sample"]:
        return [
            child for child in self.children if child.schema.uid == sample_schema.uid
        ]

    def get_child(self, name: str, item_value_type: SampleSchema) -> Optional["Sample"]:
        return next(
            (
                child
                for child in self.get_children_of_type(item_value_type)
                if child.name == name
            ),
            None,
        )

    @classmethod
    def get_or_add_child(
        cls,
        name: str,
        item_value_type: SampleSchema,
        parents: Sequence["Sample"],
        attributes: Optional[Sequence[Attribute]] = None,
        commit: bool = True,
    ) -> "Sample":
        # Check if any of the parents already have the child
        child = next(
            (
                child
                for child in (
                    parent.get_child(name, item_value_type) for parent in parents
                )
                if child is not None
            ),
            None,
        )

        if child is not None:
            # Add all parents to child
            child.parents = list(parents)
        else:
            # Create a new child
            child = cls(
                parents[0].project,
                name,
                item_value_type,
                parents,
                attributes,
                commit,
            )
        return child

    def get_image(self, name: str) -> Optional[Image]:
        return next((image for image in self.images if image.name == name), None)

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

    def get_parents_of_type(
        self, sample_type: SampleSchema, recurse: bool = False
    ) -> Set["Sample"]:
        parents: Set[Sample] = set()
        for parent in self.parents:
            if parent.schema == sample_type:
                parents.add(parent)
            if recurse:
                parents.update(parent.get_parents_of_type(sample_type, True))
        return parents

    def set_parents(self, parents: Iterable[Sample], commit: bool = True):
        self.parents = list(parents)
        if commit:
            db.session.commit()

    def set_children(self, children: Iterable[Sample], commit: bool = True):
        self.children = list(children)
        if commit:
            db.session.commit()

    def copy(self) -> Sample:
        return Sample(
            self.project,
            f"{self.name} (copy)",
            self.schema,
            self.parents,
            [attribute.copy() for attribute in self.attributes.values()],
            False,
            False,
        )


class Project(DbBase):
    """Represents a project containing samples, images, annotations, and
    observations."""

    uid: Mapped[UUID] = db.Column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = db.Column(db.String(128))
    status: Mapped[ProjectStatus] = db.Column(db.Enum(ProjectStatus))

    # Relations
    schema: Mapped[Schema] = db.relationship(Schema)  # type: ignore

    # For relations
    schema_uid: Mapped[UUID] = db.Column(Uuid, db.ForeignKey("schema.uid"))

    def __init__(
        self, name: str, schema: Schema, add: bool = True, commit: bool = True
    ):
        """Create a project.

        Parameters
        ----------
        name: str
            Name of project.

        """
        super().__init__(
            name=name,
            schema=schema,
            status=ProjectStatus.INITIALIZED,
            add=add,
            commit=commit,
        )

    def __str__(self) -> str:
        return f"Project id: {self.uid}, name {self.name}, " f"status: {self.status}."

    @property
    def initialized(self) -> bool:
        """Return True if project have status 'INITIALIZED'."""
        return self.status == ProjectStatus.INITIALIZED

    @property
    def metadata_searching(self) -> bool:
        """Return True if project have status 'METADATA_SEARCHING'."""
        return self.status == ProjectStatus.METADATA_SEARCHING

    @property
    def metadata_search_complete(self) -> bool:
        """Return True if project have status 'SEARCH_COMPLETE'."""
        return self.status == ProjectStatus.METEDATA_SEARCH_COMPLETE

    @property
    def image_pre_processing(self) -> bool:
        """Return True if project have status 'IMAGE_PRE_PROCESSING'."""
        return self.status == ProjectStatus.IMAGE_PRE_PROCESSING

    @property
    def image_pre_processing_complete(self) -> bool:
        """Return True if project have status 'IMAGE_PRE_PROCESSING_COMPLETE'."""
        return self.status == ProjectStatus.IMAGE_PRE_PROCESSING_COMPLETE

    @property
    def image_post_processing(self) -> bool:
        """Return True if project have status 'IMAGE_POST_PROCESSING'."""
        return self.status == ProjectStatus.IMAGE_POST_PROCESSING

    @property
    def image_post_processing_complete(self) -> bool:
        """Return True if project have status 'IMAGE_POST_PROCESSING_COMPLETE'."""
        return self.status == ProjectStatus.IMAGE_POST_PROCESSING_COMPLETE

    @property
    def exporting(self) -> bool:
        """Return True if project have status 'EXPORTING'."""
        return self.status == ProjectStatus.EXPORTING

    @property
    def export_complete(self) -> bool:
        """Return True if project have status 'EXPORT_COMPLETE'."""
        return self.status == ProjectStatus.EXPORT_COMPLETE

    @property
    def failed(self) -> bool:
        """Return True if project have status 'FAILED'."""
        return self.status == ProjectStatus.FAILED

    @property
    def deleted(self) -> bool:
        return self.status == ProjectStatus.DELETED

    @property
    def items(self) -> Sequence[ProjectItem]:
        return [
            ProjectItem(
                schema=item_schema,
                count=Item.get_count_for_project(self.uid, item_schema.uid, True),
            )
            for item_schema in ItemSchema.get_for_schema(self.schema.uid)
        ]

    @property
    def item_schemas(self) -> Sequence[ItemSchema]:
        return ItemSchema.get_for_schema(self.schema.uid)

    @property
    def item_counts(self) -> List[int]:
        return [
            Item.get_count_for_project(self.uid, item_schema.uid, True)
            for item_schema in ItemSchema.get_for_schema(self.schema.uid)
        ]

    @property
    def is_valid(self) -> bool:
        return all(
            item.is_valid for item in Item.get_for_project(self.uid, selected=True)
        )

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
    def get_all_projects(cls) -> Sequence["Project"]:
        """Return all projects
        Returns
        ----------
        List[Project]
            List of projects.
        """
        return db.session.scalars(select(cls)).all()

    def reset(self):
        """Reset status."""
        allowed_statuses = [
            ProjectStatus.INITIALIZED,
            ProjectStatus.METADATA_SEARCHING,
            ProjectStatus.METEDATA_SEARCH_COMPLETE,
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
                f"{ProjectStatus.METEDATA_SEARCH_COMPLETE}, was {self.status}"
            )
        self.status = ProjectStatus.METEDATA_SEARCH_COMPLETE
        current_app.logger.debug(f"Project {self.uid} set as search complete.")
        db.session.commit()

    def set_as_pre_processing(self):
        """Set project as 'PRE_PROCESSING' if not started."""
        if not self.metadata_search_complete:
            raise NotAllowedActionError(
                f"Can only set {ProjectStatus.METEDATA_SEARCH_COMPLETE} project as "
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
                Image.status != ImageStatus.FAILED,
                Image.status != ImageStatus.POST_PROCESSED,
            )
        ).first()
        if any_non_completed is not None:
            current_app.logger.debug(f"Project {self.uid} not yet completed.")
            return
        any_failed = db.session.scalars(
            images_for_project.filter(Image.status == ImageStatus.FAILED)
        ).first()

        if any_failed:
            self.set_as_failed()
        else:
            self.set_as_post_processed()

    def set_status_if_all_images_pre_processed(self):
        if self.failed:
            return
        images_for_project = select(Image).filter_by(project_uid=self.uid)

        any_non_completed = db.session.scalars(
            images_for_project.filter(
                Image.status != ImageStatus.FAILED,
                Image.status != ImageStatus.PRE_PROCESSED,
            )
        ).first()
        if any_non_completed is not None:
            current_app.logger.debug(
                f"Project {self.uid} not yet finished pre-processing."
            )
            return
        any_failed = db.session.scalars(
            images_for_project.filter(Image.status == ImageStatus.FAILED)
        ).first()

        if any_failed:
            self.set_as_failed()
        else:
            self.set_as_pre_processed()
