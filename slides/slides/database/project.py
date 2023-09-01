"""Project and Sample, Annotations, Observations, Images."""
from __future__ import annotations

from abc import abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Type, TypeVar, Union, Any
from uuid import UUID, uuid4

from sqlalchemy import Uuid, delete, func, select
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm.collections import attribute_mapped_collection

from slides.database.attribute import Attribute
from slides.database.db import NotAllowedActionError, NotFoundError, db
from slides.database.schema import (
    AnnotationSchema,
    ImageSchema,
    ItemSchema,
    ItemValueType,
    ObservationSchema,
    SampleSchema,
    Schema,
)
from slides.model import ImageStatus, ProjectStatus

ItemType = TypeVar("ItemType", bound="Item")


class Item(db.Model):
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
            project=project,
            name=name,
            attributes=attributes,
            **kwargs,
        )
        db.session.add(self)
        db.session.commit()

    @property
    def schema(self) -> ItemSchema:
        raise NotImplementedError()

    @property
    def schema_name(self) -> str:
        return self.schema.name

    @property
    def schema_display_name(self) -> str:
        return self.schema.display_name

    @abstractmethod
    def select(self, value: bool):
        """Should select or de-select the item."""
        raise NotImplementedError()

    @classmethod
    def get(cls: Type[ItemType], uid: UUID) -> Optional[ItemType]:
        """Return item by id."""
        return db.session.get(cls, uid)

    @classmethod
    def get_item(cls: Type[ItemType], item_uid: UUID) -> Optional[ItemType]:
        return db.session.get(cls, item_uid)

    @classmethod
    def delete_for_project(cls, project_uid: UUID, only_non_selected=False):
        query = delete(cls).where(cls.project_uid == project_uid)
        if only_non_selected:
            query = query.where(cls.selected == False)
        db.session.execute(query)
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


class Annotation(Item):
    """An annotation item. Is related to an image."""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("item.uid"), primary_key=True)

    # For relations
    image_uid: Mapped[UUID] = mapped_column(db.ForeignKey("image.uid"))

    # Relationships
    schema: Mapped[AnnotationSchema] = db.relationship(AnnotationSchema)  # type: ignore
    image: Mapped[Image] = db.relationship(
        "Image", back_populates="annotations", foreign_keys=[image_uid]
    )  # type: ignore

    __mapper_args__ = {
        "polymorphic_identity": ItemValueType.ANNOTATION,
    }


class Observation(Item):
    """An observation item. Is related to an image or a sample."""

    uid: Mapped[UUID] = mapped_column(db.ForeignKey("item.uid"), primary_key=True)

    # For relations
    image_uid: Mapped[Optional[UUID]] = mapped_column(db.ForeignKey("image.uid"))
    sample_uid: Mapped[Optional[UUID]] = mapped_column(db.ForeignKey("sample.uid"))

    # Relationships
    schema: Mapped[ObservationSchema] = db.relationship(ObservationSchema)  # type: ignore
    image: Mapped[Optional[Image]] = db.relationship(
        "Image", back_populates="observations", foreign_keys=[image_uid]
    )  # type: ignore
    sample: Mapped[Optional[Sample]] = db.relationship(
        "Sample", back_populates="observations", foreign_keys=[sample_uid]
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
        item: Union["Sample", "Image"],
        attributes: Optional[Sequence[Attribute]] = None,
    ):
        kwargs = {}
        if isinstance(item, Sample):
            kwargs["sample"] = item
        elif isinstance(item, Image):
            kwargs["image"] = item
        super().__init__(
            name=name,
            project=project,
            attributes=attributes,
            schema=observation_schema,
            **kwargs,
        )

    @property
    def item(self) -> Union["Image", "Sample"]:
        """Return the item the observation is related to, either an image or
        a sample."""
        if self.image is not None:
            return self.image
        return self.sample

    def select(self, value: bool):
        self.selected = value
        self.item.select_from_child(value)

    def select_from_sample(self, value: bool):
        self.selected = value


class ImageFile(db.Model):
    """Represents a file stored for an image."""

    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("item.uid"), primary_key=True, default=uuid4
    )
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

    def __init__(self, filename: str):
        """A file stored for a image.

        Parameters
        ----------
        filename: Name of file relative to image folder.

        """
        super().__init__(filename=filename)
        db.session.add(self)
        db.session.commit()


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
    uid: Mapped[UUID] = mapped_column(db.ForeignKey("item.uid"), primary_key=True)
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
        )

    @property
    def not_started(self) -> bool:
        return self.status == ImageStatus.NOT_STARTED

    @property
    def downloading(self) -> bool:
        return self.status == ImageStatus.DOWNLOADING

    @property
    def processing(self) -> bool:
        return self.status == ImageStatus.PROCESSING

    @property
    def failed(self) -> bool:
        return self.status == ImageStatus.FAILED

    @property
    def completed(self) -> bool:
        return self.status == ImageStatus.COMPLETED

    def set_as_downloading(self):
        if not self.not_started:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.NOT_STARTED} "
                f"image as {ImageStatus.DOWNLOADING}"
            )
        self.status = ImageStatus.DOWNLOADING
        db.session.commit()

    def set_as_processing(self):
        if not self.downloading:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.DOWNLOADING} "
                f"image as {ImageStatus.PROCESSING}"
            )
        self.status = ImageStatus.PROCESSING
        db.session.commit()

    def set_as_failed(self):
        self.status = ImageStatus.FAILED
        db.session.commit()

    def set_as_completed(self):
        if not self.processing:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.PROCESSING} "
                f"image as {ImageStatus.COMPLETED}"
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
    def get_or_add_image(
        cls,
        name: str,
        image_type: ImageSchema,
        samples: Sequence["Sample"],
        attributes: Optional[Sequence[Attribute]] = None,
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

    @classmethod
    def get_images_with_thumbnails(cls, project: Project) -> Sequence["Image"]:
        """Return image id with thumbnail."""
        return db.session.scalars(
            select(Image).filter(
                cls.project_uid == project.uid, cls.thumbnail_path != None
            )
        ).all()


class Sample(Item):
    uid: Mapped[UUID] = mapped_column(db.ForeignKey("item.uid"), primary_key=True)

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
        )
        db.session.commit()

    def get_children_of_type(self, sample_schema: SampleSchema) -> List["Sample"]:
        return [child for child in self.children if child.schema == sample_schema]

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
    ) -> List["Sample"]:
        parents: List[Sample] = []
        for parent in self.parents:
            if parent.schema == sample_type:
                parents.append(parent)
            if recurse:
                parents.extend(parent.get_parents_of_type(sample_type, True))
        return parents


class Project(db.Model):
    """Represents a project containing samples, images, annotations, and
    observations."""

    uid: Mapped[UUID] = db.Column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = db.Column(db.String(128))
    status: Mapped[ProjectStatus] = db.Column(db.Enum(ProjectStatus))

    # Relations
    schema: Mapped[Schema] = db.relationship(Schema)  # type: ignore

    # For relations
    schema_uid: Mapped[UUID] = db.Column(Uuid, db.ForeignKey("schema.uid"))

    def __init__(self, name: str, schema: Schema):
        """Create a project.

        Parameters
        ----------
        name: str
            Name of project.

        """
        super().__init__(name=name, schema=schema, status=ProjectStatus.INITIALIZED)
        db.session.add(self)
        db.session.commit()

    def __str__(self) -> str:
        return f"Project id: {self.uid}, name {self.name}, " f"status: {self.status}."

    @property
    def initialized(self) -> bool:
        """Return True if project have status 'INITIALIZED'."""
        return self.status == ProjectStatus.INITIALIZED

    @property
    def searching(self) -> bool:
        """Return True if project have status 'SEARCHING'."""
        return self.status == ProjectStatus.SEARCHING

    @property
    def search_complete(self) -> bool:
        """Return True if project have status 'SEARCH_COMPLETE'."""
        return self.status == ProjectStatus.SEARCH_COMPLETE

    @property
    def started(self) -> bool:
        """Return True if  project have status 'STARTED'."""
        return self.status == ProjectStatus.STARTED

    @property
    def failed(self) -> bool:
        """Return True if project have status 'FAILED'."""
        return self.status == ProjectStatus.FAILED

    @property
    def completed(self) -> bool:
        """Return True if project have status 'COMPLETED'."""
        return self.status == ProjectStatus.COMPLETED

    @property
    def submitted(self) -> bool:
        """Return True if project have status 'SUMBITTED'."""
        return self.status == ProjectStatus.SUBMITTED

    @property
    def deleted(self) -> bool:
        return self.status == ProjectStatus.DELETED

    @property
    def item_schemas(self) -> Sequence[ItemSchema]:
        return ItemSchema.get_for_schema(self.schema)

    @property
    def item_counts(self) -> List[int]:
        return [
            Item.get_count_for_project(self.uid, item_schema.uid, True)
            for item_schema in ItemSchema.get_for_schema(self.schema)
        ]

    @classmethod
    def get_project(cls, uid: UUID) -> Optional["Project"]:
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
            ProjectStatus.SEARCHING,
            ProjectStatus.SEARCH_COMPLETE,
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

        if self.started:
            return
        self.status = ProjectStatus.DELETED
        db.session.delete(self)
        db.session.commit()

    def set_as_searching(self):
        """Set project as 'SEARCHING' if not started."""
        if not self.initialized:
            raise NotAllowedActionError(
                f"Can only set {ProjectStatus.INITIALIZED} project as "
                f"{ProjectStatus.SEARCHING}, was {self.status}"
            )
        self.status = ProjectStatus.SEARCHING
        db.session.commit()

    def set_as_search_complete(self):
        """Set project as 'SEARCH_COMPLETE' if not started."""
        if not self.searching:
            raise NotAllowedActionError(
                f"Can only set {ProjectStatus.SEARCHING} project as "
                f"{ProjectStatus.SEARCH_COMPLETE}, was {self.status}"
            )
        self.status = ProjectStatus.SEARCH_COMPLETE
        db.session.commit()

    def set_as_started(self):
        """Set status of project to 'STARTED'."""
        if not self.search_complete:
            raise NotAllowedActionError(
                f"Can only set {ProjectStatus.SEARCH_COMPLETE} project as "
                f"{ProjectStatus.STARTED}, was {self.status}"
            )
        self.status = ProjectStatus.STARTED
        db.session.commit()

    def set_as_completed(self):
        """Set status of project to 'COMPLETED'."""
        if not self.started:
            raise NotAllowedActionError(
                f"Can only set {ProjectStatus.STARTED} project as"
                f"{ProjectStatus.COMPLETED}, was {self.status}"
            )
        self.status = ProjectStatus.COMPLETED
        db.session.commit()

    def set_as_submitted(self):
        """Set status of project to 'SUBMITTED'."""
        if not (self.completed):
            raise NotAllowedActionError(
                f"Can only set {ProjectStatus.COMPLETED} project as"
                f"{ProjectStatus.SUBMITTED}, was {self.status}"
            )
        self.status = ProjectStatus.SUBMITTED
        db.session.commit()

    def set_as_failed(self):
        """Set status of project to 'FAILED'."""
        self.status = ProjectStatus.FAILED
        db.session.commit()

    def update(self):
        db.session.commit()

    def set_status_if_finished(self):
        if self.failed:
            return
        images_for_project = select(Image).filter_by(project_uid=self.uid)

        any_non_completed = db.session.scalars(
            images_for_project.filter(
                Image.status != ImageStatus.FAILED,
                Image.status != ImageStatus.COMPLETED,
            )
        ).first()
        if any_non_completed is not None:
            print(f"project {self.uid} not completed")
            return
        any_failed = db.session.scalars(
            images_for_project.filter(Image.status == ImageStatus.FAILED)
        ).first()

        if any_failed:
            self.set_as_failed()
        else:
            self.set_as_completed()
