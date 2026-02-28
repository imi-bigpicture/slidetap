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
from collections import defaultdict
from typing import (
    Any,
    Dict,
    Generic,
    Iterable,
    List,
    Optional,
    Set,
    TypeVar,
    Union,
)
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Column, Enum, ForeignKey, String, Table, Uuid
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from slidetap.database.attribute import DatabaseAttribute
from slidetap.database.db import Base, NotAllowedActionError
from slidetap.database.project import DatabaseBatch, DatabaseDataset
from slidetap.model import (
    Annotation,
    Image,
    ImageFile,
    ImageFormat,
    ImageStatus,
    ItemType,
    ItemValueType,
    Observation,
    Sample,
)
from slidetap.model.item_reference import ItemReference
from slidetap.model.tag import Tag

DatabaseItemType = TypeVar("DatabaseItemType", bound="DatabaseItem")


class DatabaseTag(Base):
    uid: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(32))
    description: Mapped[Optional[str]] = mapped_column(String(512))
    color: Mapped[Optional[str]] = mapped_column(String(7))

    __tablename__ = "tag"

    def __init__(
        self,
        name: str,
        description: Optional[str] = None,
        color: Optional[str] = None,
        uid: Optional[UUID] = None,
    ):
        """Create a tag.

        Parameters
        ----------
        name: str
            Name of the tag.
        description: Optional[str]
            Description of the tag.
        color: Optional[str]
            Color of the tag, in hex format (e.g., "FF5733").
        uid: Optional[UUID]
            Unique identifier for the tag.
        """
        super().__init__(
            uid=uid if (uid and uid != UUID(int=0)) else uuid4(),
            name=name,
            description=description,
            color=color,
        )

    @property
    def model(self) -> Tag:
        return Tag(
            uid=self.uid,
            name=self.name,
            description=self.description,
            color=self.color,
        )


class DatabaseItem(Base, Generic[ItemType]):
    """Base class for an metadata item."""

    # Table for mapping many-to-many items to tags
    item_to_tag = Table(
        "item_to_tag",
        Base.metadata,
        Column(
            "item_uid",
            Uuid,
            ForeignKey("item.uid"),
            primary_key=True,
        ),
        Column(
            "tag_uid",
            Uuid,
            ForeignKey("tag.uid"),
            primary_key=True,
        ),
    )

    uid: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    identifier: Mapped[str] = mapped_column(String(128))
    name: Mapped[Optional[str]] = mapped_column(String(128))
    external_identifier: Mapped[Optional[str]] = mapped_column(String(128))
    pseudonym: Mapped[Optional[str]] = mapped_column(String(128))
    selected: Mapped[bool] = mapped_column(Boolean, default=True)
    comment: Mapped[Optional[str]] = mapped_column(String(512))

    valid_attributes: Mapped[bool] = mapped_column(Boolean, default=False)
    valid_relations: Mapped[bool] = mapped_column(Boolean, default=False)
    item_value_type: Mapped[ItemValueType] = mapped_column(
        Enum(ItemValueType), index=True
    )
    locked: Mapped[bool] = mapped_column(Boolean, default=False)
    schema_uid: Mapped[UUID] = mapped_column(Uuid, index=True)

    # Relations
    attributes: Mapped[Set[DatabaseAttribute[Any, Any]]] = relationship(
        DatabaseAttribute,
        cascade="all, delete-orphan",
        foreign_keys="DatabaseAttribute.attribute_item_uid",
    )
    private_attributes: Mapped[Set[DatabaseAttribute[Any, Any]]] = relationship(
        DatabaseAttribute,
        cascade="all, delete-orphan",
        foreign_keys="DatabaseAttribute.private_attribute_item_uid",
    )
    dataset: Mapped[DatabaseDataset] = relationship(DatabaseDataset)
    batch: Mapped[Optional[DatabaseBatch]] = relationship(DatabaseBatch)
    tags: Mapped[Set[DatabaseTag]] = relationship("DatabaseTag", secondary=item_to_tag)

    # For relations
    dataset_uid: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("dataset.uid"), index=True
    )
    batch_uid: Mapped[UUID] = mapped_column(Uuid, ForeignKey("batch.uid"), index=True)

    __mapper_args__ = {
        "polymorphic_on": "item_value_type",
    }
    __tablename__ = "item"

    def __init__(
        self,
        dataset_uid: UUID,
        batch_uid: Optional[UUID],
        schema_uid: UUID,
        identifier: str,
        name: Optional[str],
        external_identifier: Optional[str],
        pseudonym: Optional[str],
        attributes: Optional[List[DatabaseAttribute]],
        private_attributes: Optional[List[DatabaseAttribute]],
        tags: Optional[List[DatabaseTag]],
        comment: Optional[str],
        selected: bool,
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
        external_identifier: Optional[str]
            Optional external identifier of the item.
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
        super().__init__(
            dataset_uid=dataset_uid,
            batch_uid=batch_uid,
            schema_uid=schema_uid,
            identifier=identifier,
            name=name,
            external_identifier=external_identifier,
            pseudonym=pseudonym,
            attributes=set(attributes) if attributes else set(),
            private_attributes=set(private_attributes) if private_attributes else set(),
            tags=set(tags) if tags else set(),
            comment=comment,
            selected=selected,
            uid=uid if (uid and uid != UUID(int=0)) else uuid4(),
        )

    @hybrid_property
    def valid(self) -> bool:
        return (
            self.valid_attributes is not None
            and self.valid_attributes
            and self.valid_relations is not None
            and self.valid_relations
        )

    @property
    @abstractmethod
    def model(self) -> ItemType:
        raise NotImplementedError()

    @property
    def reference(self) -> ItemReference:
        return ItemReference(
            uid=self.uid,
            identifier=self.identifier,
        )


class DatabaseObservation(DatabaseItem[Observation]):
    """An observation item. Is related to an image or a sample."""

    uid: Mapped[UUID] = mapped_column(
        ForeignKey("item.uid", ondelete="CASCADE"), primary_key=True
    )

    # For relations
    image_uid: Mapped[Optional[UUID]] = mapped_column(ForeignKey("image.uid"))
    sample_uid: Mapped[Optional[UUID]] = mapped_column(ForeignKey("sample.uid"))
    annotation_uid: Mapped[Optional[UUID]] = mapped_column(ForeignKey("annotation.uid"))

    # Relationships
    image: Mapped[Optional[DatabaseImage]] = relationship(
        "DatabaseImage", back_populates="observations", foreign_keys=[image_uid]
    )  # type: ignore
    sample: Mapped[Optional[DatabaseSample]] = relationship(
        "DatabaseSample", back_populates="observations", foreign_keys=[sample_uid]
    )  # type: ignore
    annotation: Mapped[Optional[DatabaseAnnotation]] = relationship(
        "DatabaseAnnotation",
        back_populates="observations",
        foreign_keys=[annotation_uid],
    )  # type: ignore

    __mapper_args__ = {
        "polymorphic_identity": ItemValueType.OBSERVATION,
    }
    __tablename__ = "observation"

    def __init__(
        self,
        dataset_uid: UUID,
        batch_uid: Optional[UUID],
        schema_uid: UUID,
        identifier: str,
        item: Optional[
            Union["DatabaseAnnotation", "DatabaseImage", "DatabaseSample"]
        ] = None,
        attributes: Optional[List[DatabaseAttribute]] = None,
        private_attributes: Optional[List[DatabaseAttribute]] = None,
        tags: Optional[List[DatabaseTag]] = None,
        comment: Optional[str] = None,
        name: Optional[str] = None,
        external_identifier: Optional[str] = None,
        pseudonym: Optional[str] = None,
        selected: bool = True,
        uid: Optional[UUID] = None,
    ):
        super().__init__(
            dataset_uid=dataset_uid,
            batch_uid=batch_uid,
            schema_uid=schema_uid,
            identifier=identifier,
            name=name,
            external_identifier=external_identifier,
            pseudonym=pseudonym,
            selected=selected,
            attributes=attributes,
            private_attributes=private_attributes,
            tags=tags,
            comment=comment,
            uid=uid if uid != UUID(int=0) else None,
        )
        if isinstance(item, DatabaseImage):
            self.image = item
        elif isinstance(item, DatabaseSample):
            self.sample = item
        elif isinstance(item, DatabaseAnnotation):
            self.annotation = item

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
                attribute.tag: attribute.model for attribute in self.attributes
            },
            private_attributes={
                attribute.tag: attribute.model for attribute in self.private_attributes
            },
            dataset_uid=self.dataset_uid,
            schema_uid=self.schema_uid,
            batch_uid=self.batch_uid,
            sample=(
                (self.sample.schema_uid, self.sample.uid)
                if self.sample is not None
                else None
            ),
            image=(
                (self.image.schema_uid, self.image.uid)
                if self.image is not None
                else None
            ),
            annotation=(
                (self.annotation.schema_uid, self.annotation.uid)
                if self.annotation is not None
                else None
            ),
            comment=self.comment,
            tags=[tag.uid for tag in self.tags],
        )


class DatabaseAnnotation(DatabaseItem[Annotation]):
    """An annotation item. Is related to an image."""

    uid: Mapped[UUID] = mapped_column(
        ForeignKey("item.uid", ondelete="CASCADE"), primary_key=True
    )

    # For relations
    image_uid: Mapped[UUID] = mapped_column(ForeignKey("image.uid"))

    # Relationships
    image: Mapped[Optional[DatabaseImage]] = relationship(
        "DatabaseImage", back_populates="annotations", foreign_keys=[image_uid]
    )  # type: ignore
    observations: Mapped[Set[DatabaseObservation]] = relationship(
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
        dataset_uid: UUID,
        batch_uid: Optional[UUID],
        schema_uid: UUID,
        identifier: str,
        image: Optional[DatabaseImage] = None,
        attributes: Optional[List[DatabaseAttribute]] = None,
        private_attributes: Optional[List[DatabaseAttribute]] = None,
        tags: Optional[List[DatabaseTag]] = None,
        comment: Optional[str] = None,
        name: Optional[str] = None,
        external_identifier: Optional[str] = None,
        pseudonym: Optional[str] = None,
        selected: bool = True,
        uid: Optional[UUID] = None,
    ):
        super().__init__(
            dataset_uid=dataset_uid,
            batch_uid=batch_uid,
            schema_uid=schema_uid,
            identifier=identifier,
            attributes=attributes,
            private_attributes=private_attributes,
            tags=tags,
            comment=comment,
            name=name,
            external_identifier=external_identifier,
            pseudonym=pseudonym,
            selected=selected,
            uid=uid if uid != UUID(int=0) else None,
        )
        self.image = image

    @property
    def model(self) -> Annotation:
        observations = defaultdict(list)
        for observation in self.observations:
            observations[observation.dataset_uid].append(observation.uid)
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
                attribute.tag: attribute.model for attribute in self.attributes
            },
            private_attributes={
                attribute.tag: attribute.model for attribute in self.private_attributes
            },
            dataset_uid=self.dataset_uid,
            schema_uid=self.schema_uid,
            batch_uid=self.batch_uid,
            image=(
                (self.image.schema_uid, self.image.uid)
                if self.image is not None
                else None
            ),
            obseration=observations,
            comment=self.comment,
            tags=[tag.uid for tag in self.tags],
        )


class DatabaseImageFile(Base):
    """Represents a file stored for an image."""

    uid: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    filename: Mapped[str] = mapped_column(String(512))

    # For relations
    # TODO should optional be allowed here?
    image_uid: Mapped[UUID] = mapped_column(ForeignKey("image.uid"))

    # Relations
    image: Mapped[DatabaseImage] = relationship(
        "DatabaseImage",
        back_populates="files",
        foreign_keys=[image_uid],
    )  # type: ignore

    __tablename__ = "image_file"

    def __init__(self, image: DatabaseImage, filename: str):
        """A file stored for a image.

        Parameters
        ----------
        filename: Name of file relative to image folder.

        """
        super().__init__(image=image, filename=filename, uid=uuid4())

    @property
    def model(self) -> ImageFile:
        return ImageFile(uid=self.uid, filename=self.filename)


class DatabaseImage(DatabaseItem[Image]):
    # Table for mapping many-to-many samples to images
    sample_to_image = Table(
        "sample_to_image",
        Base.metadata,
        Column(
            "sample_uid",
            Uuid,
            ForeignKey("sample.uid"),
            primary_key=True,
        ),
        Column(
            "image_uid",
            Uuid,
            ForeignKey("image.uid"),
            primary_key=True,
        ),
    )
    uid: Mapped[UUID] = mapped_column(
        ForeignKey("item.uid", ondelete="CASCADE"), primary_key=True
    )

    folder_path: Mapped[Optional[str]] = mapped_column(String(512))
    thumbnail_path: Mapped[Optional[str]] = mapped_column(String(512))

    status: Mapped[ImageStatus] = mapped_column(Enum(ImageStatus))
    status_message: Mapped[Optional[str]] = mapped_column(String(512))
    format: Mapped[ImageFormat] = mapped_column(Enum(ImageFormat))
    # Relationship
    samples: Mapped[Set[DatabaseSample]] = relationship(
        "DatabaseSample", secondary=sample_to_image, back_populates="images"
    )  # type: ignore
    annotations: Mapped[Set[DatabaseAnnotation]] = relationship(
        DatabaseAnnotation,
        back_populates="image",
        foreign_keys=[DatabaseAnnotation.image_uid],
    )  # type: ignore
    observations: Mapped[Set[DatabaseObservation]] = relationship(
        DatabaseObservation,
        back_populates="image",
        foreign_keys=[DatabaseObservation.image_uid],
    )  # type: ignore
    files: Mapped[Set[DatabaseImageFile]] = relationship(
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
        dataset_uid: UUID,
        batch_uid: Optional[UUID],
        schema_uid: UUID,
        identifier: str,
        format: ImageFormat,
        samples: Optional[Union["DatabaseSample", Iterable["DatabaseSample"]]] = None,
        attributes: Optional[List[DatabaseAttribute]] = None,
        private_attributes: Optional[List[DatabaseAttribute]] = None,
        tags: Optional[List[DatabaseTag]] = None,
        comment: Optional[str] = None,
        name: Optional[str] = None,
        pseudonym: Optional[str] = None,
        external_identifier: Optional[str] = None,
        selected: bool = True,
        folder_path: Optional[str] = None,
        thumbnail_path: Optional[str] = None,
        uid: Optional[UUID] = None,
    ):
        self.status = ImageStatus.NOT_STARTED
        super().__init__(
            dataset_uid=dataset_uid,
            batch_uid=batch_uid,
            schema_uid=schema_uid,
            identifier=identifier,
            attributes=attributes,
            private_attributes=private_attributes,
            tags=tags,
            comment=comment,
            name=name,
            external_identifier=external_identifier,
            pseudonym=pseudonym,
            selected=selected,
            uid=uid if uid != UUID(int=0) else None,
        )
        if samples is not None:
            if not isinstance(samples, Iterable):
                samples = [samples]
            self.samples = set(samples)
        self.folder_path = folder_path
        self.thumbnail_path = thumbnail_path
        self.format = format

    @hybrid_property
    def valid(self) -> bool:
        return (
            self.valid_attributes is not None
            and self.valid_attributes
            and self.valid_relations is not None
            and self.valid_relations
            and not self.failed
        )

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
        samples: Dict[UUID, List[UUID]] = defaultdict(list)
        for sample in self.samples:
            samples[sample.schema_uid].append(sample.uid)
        annotations: Dict[UUID, List[UUID]] = defaultdict(list)
        for annotation in self.annotations:
            annotations[annotation.schema_uid].append(annotation.uid)
        observations: Dict[UUID, List[UUID]] = defaultdict(list)
        for observation in self.observations:
            observations[observation.schema_uid].append(observation.uid)
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
                attribute.tag: attribute.model for attribute in self.attributes
            },
            private_attributes={
                attribute.tag: attribute.model for attribute in self.private_attributes
            },
            dataset_uid=self.dataset_uid,
            schema_uid=self.schema_uid,
            batch_uid=self.batch_uid,
            external_identifier=self.external_identifier,
            folder_path=self.folder_path,
            thumbnail_path=self.thumbnail_path,
            status=self.status,
            status_message=self.status_message,
            files=[file.model for file in self.files],
            samples=samples,
            annotations=annotations,
            observations=observations,
            comment=self.comment,
            tags=[tag.uid for tag in self.tags],
            format=self.format,
        )

    def set_as_downloading(self):
        if not self.not_started:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.NOT_STARTED} image as "
                f"{ImageStatus.DOWNLOADING}, was {self.status}."
            )
        self.status = ImageStatus.DOWNLOADING

    def reset_as_not_started(self):
        if not self.downloading_failed:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.DOWNLOADING_FAILED} image as {ImageStatus.NOT_STARTED}, was {self.status}."
            )
        self.status = ImageStatus.NOT_STARTED

    def set_as_downloading_failed(self):
        if not self.downloading:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.DOWNLOADING} image as "
                f"{ImageStatus.DOWNLOADING_FAILED}, was {self.status}."
            )
        self.status = ImageStatus.DOWNLOADING_FAILED
        # self.valid = False

    def set_as_downloaded(self):
        if not self.downloading:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.DOWNLOADING} image as "
                f"{ImageStatus.DOWNLOADED}, was {self.status}."
            )
        self.status = ImageStatus.DOWNLOADED

    def set_as_pre_processing(self):
        if not self.downloaded:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.DOWNLOADED} image as "
                f"{ImageStatus.PRE_PROCESSING}, was {self.status}."
            )
        self.status = ImageStatus.PRE_PROCESSING

    def set_as_pre_processing_failed(self):
        if not self.pre_processing:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.PRE_PROCESSING} image as "
                f"{ImageStatus.PRE_PROCESSING_FAILED}, was {self.status}."
            )
        self.status = ImageStatus.PRE_PROCESSING_FAILED

    def set_as_pre_processed(self, force: bool = False):
        if not self.pre_processing and not (force and self.post_processing):
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.PRE_PROCESSING} image as "
                f"{ImageStatus.PRE_PROCESSED}, was {self.status}."
            )
        self.status = ImageStatus.PRE_PROCESSED

    def reset_as_downloaded(self):
        if not self.pre_processing_failed:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.PRE_PROCESSING_FAILED} image as "
                f"{ImageStatus.DOWNLOADED}, was {self.status}."
            )
        self.status = ImageStatus.DOWNLOADED

    def reset_as_pre_processed(self):
        if not self.post_precssing_failed:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.POST_PROCESSING_FAILED} image as "
                f"{ImageStatus.PRE_PROCESSED}, was {self.status}."
            )
        self.status = ImageStatus.PRE_PROCESSED

    def set_as_post_processing(self):
        if not self.pre_processed:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.PRE_PROCESSED} image as "
                f"{ImageStatus.POST_PROCESSING}, was {self.status}."
            )
        self.status = ImageStatus.POST_PROCESSING

    def set_as_post_processing_failed(self):
        if not self.post_processing:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.POST_PROCESSING} image as "
                f"{ImageStatus.POST_PROCESSING_FAILED}, was {self.status}."
            )
        self.status = ImageStatus.POST_PROCESSING_FAILED

    def set_as_post_processed(self):
        if not self.post_processing:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.POST_PROCESSING} image as "
                f"{ImageStatus.POST_PROCESSED}, was {self.status}."
            )
        self.status = ImageStatus.POST_PROCESSED


class DatabaseSample(DatabaseItem[Sample]):
    uid: Mapped[UUID] = mapped_column(
        ForeignKey("item.uid", ondelete="CASCADE"), primary_key=True
    )

    # Table for mapping many-to-many samples to samples.
    sample_to_sample = Table(
        "sample_to_sample",
        Base.metadata,
        Column(
            "parent_uid",
            Uuid,
            ForeignKey("sample.uid"),
            primary_key=True,
        ),
        Column(
            "child_uid",
            Uuid,
            ForeignKey("sample.uid"),
            primary_key=True,
        ),
    )

    # Relations
    children: Mapped[Set[DatabaseSample]] = relationship(
        "DatabaseSample",
        secondary=sample_to_sample,
        primaryjoin=(uid == sample_to_sample.c.parent_uid),
        secondaryjoin=(uid == sample_to_sample.c.child_uid),
        back_populates="parents",
        cascade="all, delete",
    )  # type: ignore
    parents: Mapped[Set[DatabaseSample]] = relationship(
        "DatabaseSample",
        secondary=sample_to_sample,
        primaryjoin=(uid == sample_to_sample.c.child_uid),
        secondaryjoin=(uid == sample_to_sample.c.parent_uid),
        back_populates="children",
    )  # type: ignore
    images: Mapped[Set[DatabaseImage]] = relationship(
        DatabaseImage, secondary=DatabaseImage.sample_to_image, back_populates="samples"
    )  # type: ignore
    observations: Mapped[Set[DatabaseObservation]] = relationship(
        DatabaseObservation,
        back_populates="sample",
        foreign_keys=[DatabaseObservation.sample_uid],
    )  # type: ignore

    __mapper_args__ = {
        "polymorphic_identity": ItemValueType.SAMPLE,
    }
    __tablename__ = "sample"

    def __init__(
        self,
        dataset_uid: UUID,
        batch_uid: Optional[UUID],
        schema_uid: UUID,
        identifier: str,
        parents: Optional[Union["DatabaseSample", Iterable["DatabaseSample"]]] = None,
        children: Optional[Union["DatabaseSample", Iterable["DatabaseSample"]]] = None,
        attributes: Optional[List[DatabaseAttribute]] = None,
        private_attributes: Optional[List[DatabaseAttribute]] = None,
        tags: Optional[List[DatabaseTag]] = None,
        comment: Optional[str] = None,
        name: Optional[str] = None,
        external_identifier: Optional[str] = None,
        pseudonym: Optional[str] = None,
        selected: bool = True,
        uid: Optional[UUID] = None,
    ):
        super().__init__(
            dataset_uid=dataset_uid,
            batch_uid=batch_uid,
            schema_uid=schema_uid,
            identifier=identifier,
            name=name,
            external_identifier=external_identifier,
            pseudonym=pseudonym,
            attributes=attributes,
            private_attributes=private_attributes,
            tags=tags,
            comment=comment,
            selected=selected,
            uid=uid if uid != UUID(int=0) else None,
        )
        if parents is not None:
            if not isinstance(parents, Iterable):
                parents = [parents]
            self.parents = set(parents)
        if children is not None:
            if not isinstance(children, Iterable):
                children = [children]
            self.children = set(children)

    @property
    def model(self) -> Sample:
        children = defaultdict(list)
        for child in self.children:
            children[child.schema_uid].append(child.uid)
        parents = defaultdict(list)
        for parent in self.parents:
            parents[parent.schema_uid].append(parent.uid)
        images = defaultdict(list)
        for image in self.images:
            images[image.schema_uid].append(image.uid)
        observations = defaultdict(list)
        for observation in self.observations:
            observations[observation.schema_uid].append(observation.uid)
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
                attribute.tag: attribute.model for attribute in self.attributes
            },
            private_attributes={
                attribute.tag: attribute.model for attribute in self.private_attributes
            },
            dataset_uid=self.dataset_uid,
            schema_uid=self.schema_uid,
            batch_uid=self.batch_uid,
            children=children,
            parents=parents,
            images=images,
            observations=observations,
            external_identifier=self.external_identifier,
            comment=self.comment,
            tags=[tag.uid for tag in self.tags],
        )
