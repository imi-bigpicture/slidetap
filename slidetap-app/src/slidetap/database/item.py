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
from collections.abc import Iterable
from typing import (
    Any,
    Generic,
    TypeVar,
)
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    Column,
    Enum,
    ForeignKey,
    String,
    Table,
    Uuid,
    and_,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from slidetap.database.attribute import DatabaseAttribute
from slidetap.database.db import Base, NotAllowedActionError
from slidetap.database.project import DatabaseBatch, DatabaseDataset
from slidetap.model import (
    Annotation,
    AnyItem,
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
    description: Mapped[str | None] = mapped_column(String(512))
    color: Mapped[str | None] = mapped_column(String(7))

    __tablename__ = "tag"

    def __init__(
        self,
        name: str,
        description: str | None = None,
        color: str | None = None,
        uid: UUID | None = None,
    ):
        """Create a tag.

        Parameters
        ----------
        name: str
            Name of the tag.
        description: str | None
            Description of the tag.
        color: str | None
            Color of the tag, in hex format (e.g., "FF5733").
        uid: UUID | None
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
    name: Mapped[str | None] = mapped_column(String(128))
    external_identifier: Mapped[str | None] = mapped_column(String(128))
    pseudonym: Mapped[str | None] = mapped_column(String(128))
    selected: Mapped[bool] = mapped_column(Boolean, default=True)
    comment: Mapped[str | None] = mapped_column(String(512))

    valid_attributes: Mapped[bool] = mapped_column(Boolean, default=False)
    valid_relations: Mapped[bool] = mapped_column(Boolean, default=False)
    valid_pseudonym: Mapped[bool] = mapped_column(Boolean, default=True)
    item_value_type: Mapped[ItemValueType] = mapped_column(
        Enum(ItemValueType), index=True
    )
    locked: Mapped[bool] = mapped_column(Boolean, default=False)
    schema_uid: Mapped[UUID] = mapped_column(Uuid, index=True)

    # Relations
    attributes: Mapped[set[DatabaseAttribute[Any, Any]]] = relationship(
        DatabaseAttribute,
        cascade="all, delete-orphan",
        foreign_keys="DatabaseAttribute.attribute_item_uid",
    )
    private_attributes: Mapped[set[DatabaseAttribute[Any, Any]]] = relationship(
        DatabaseAttribute,
        cascade="all, delete-orphan",
        foreign_keys="DatabaseAttribute.private_attribute_item_uid",
    )
    dataset: Mapped[DatabaseDataset] = relationship(DatabaseDataset)
    batch: Mapped[DatabaseBatch | None] = relationship(DatabaseBatch)
    tags: Mapped[set[DatabaseTag]] = relationship("DatabaseTag", secondary=item_to_tag)

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
        batch_uid: UUID | None,
        schema_uid: UUID,
        identifier: str,
        name: str | None,
        external_identifier: str | None,
        pseudonym: str | None,
        attributes: list[DatabaseAttribute] | None,
        private_attributes: list[DatabaseAttribute] | None,
        tags: list[DatabaseTag] | None,
        comment: str | None,
        selected: bool,
        uid: UUID | None = None,
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
        name: str | None
            Optional (short) name of the item.
        external_identifier: str | None
            Optional external identifier of the item.
        pseudonym: str | None
            Optional pseudonym of the item.
        attributes: dict[str, Any] | None
            Optional dictionary of attributes for the item.
        selected: bool
            Whether the item is selected.
        add: bool
            Add the item to the database.
        uid: UUID | None = None
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
            and self.valid_pseudonym
        )

    @valid.inplace.expression
    @classmethod
    def _valid_expression(cls):
        return and_(cls.valid_attributes, cls.valid_relations, cls.valid_pseudonym)

    @property
    @abstractmethod
    def model(self) -> AnyItem:
        raise NotImplementedError()

    @property
    def reference(self) -> ItemReference:
        return ItemReference(
            uid=self.uid,
            identifier=self.identifier,
            pseudonym=self.pseudonym,
        )


class DatabaseObservation(DatabaseItem[Observation]):
    """An observation item. Is related to an image or a sample."""

    uid: Mapped[UUID] = mapped_column(
        ForeignKey("item.uid", ondelete="CASCADE"), primary_key=True
    )

    # For relations
    image_uid: Mapped[UUID | None] = mapped_column(ForeignKey("image.uid"))
    sample_uid: Mapped[UUID | None] = mapped_column(ForeignKey("sample.uid"))
    annotation_uid: Mapped[UUID | None] = mapped_column(ForeignKey("annotation.uid"))

    # Relationships
    image: Mapped[DatabaseImage | None] = relationship(
        "DatabaseImage", back_populates="observations", foreign_keys=[image_uid]
    )
    sample: Mapped[DatabaseSample | None] = relationship(
        "DatabaseSample", back_populates="observations", foreign_keys=[sample_uid]
    )
    annotation: Mapped[DatabaseAnnotation | None] = relationship(
        "DatabaseAnnotation",
        back_populates="observations",
        foreign_keys=[annotation_uid],
    )

    __mapper_args__ = {
        "polymorphic_identity": ItemValueType.OBSERVATION,
    }
    __tablename__ = "observation"

    def __init__(
        self,
        dataset_uid: UUID,
        batch_uid: UUID | None,
        schema_uid: UUID,
        identifier: str,
        item: DatabaseAnnotation | DatabaseImage | DatabaseSample | None = None,
        attributes: list[DatabaseAttribute] | None = None,
        private_attributes: list[DatabaseAttribute] | None = None,
        tags: list[DatabaseTag] | None = None,
        comment: str | None = None,
        name: str | None = None,
        external_identifier: str | None = None,
        pseudonym: str | None = None,
        selected: bool = True,
        uid: UUID | None = None,
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
    def item(self) -> DatabaseImage | DatabaseSample | DatabaseAnnotation:
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
            valid=(
                self.valid_attributes and self.valid_relations and self.valid_pseudonym
            ),
            valid_attributes=self.valid_attributes,
            valid_relations=self.valid_relations,
            valid_pseudonym=self.valid_pseudonym,
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
                if self.sample is not None and self.sample.selected
                else None
            ),
            image=(
                (self.image.schema_uid, self.image.uid)
                if self.image is not None and self.image.selected
                else None
            ),
            annotation=(
                (self.annotation.schema_uid, self.annotation.uid)
                if self.annotation is not None and self.annotation.selected
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
    image: Mapped[DatabaseImage | None] = relationship(
        "DatabaseImage", back_populates="annotations", foreign_keys=[image_uid]
    )
    observations: Mapped[set[DatabaseObservation]] = relationship(
        DatabaseObservation,
        back_populates="annotation",
        foreign_keys=[DatabaseObservation.annotation_uid],
    )
    __mapper_args__ = {
        "polymorphic_identity": ItemValueType.ANNOTATION,
    }
    __tablename__ = "annotation"

    def __init__(
        self,
        dataset_uid: UUID,
        batch_uid: UUID | None,
        schema_uid: UUID,
        identifier: str,
        image: DatabaseImage | None = None,
        attributes: list[DatabaseAttribute] | None = None,
        private_attributes: list[DatabaseAttribute] | None = None,
        tags: list[DatabaseTag] | None = None,
        comment: str | None = None,
        name: str | None = None,
        external_identifier: str | None = None,
        pseudonym: str | None = None,
        selected: bool = True,
        uid: UUID | None = None,
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
            if observation.selected:
                observations[observation.dataset_uid].append(observation.uid)
        return Annotation(
            uid=self.uid,
            identifier=self.identifier,
            name=self.name,
            pseudonym=self.pseudonym,
            selected=self.selected,
            valid=(
                self.valid_attributes and self.valid_relations and self.valid_pseudonym
            ),
            valid_attributes=self.valid_attributes,
            valid_relations=self.valid_relations,
            valid_pseudonym=self.valid_pseudonym,
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
                if self.image is not None and self.image.selected
                else None
            ),
            observation=observations,
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
    )
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

    folder_path: Mapped[str | None] = mapped_column(String(512))
    thumbnail_path: Mapped[str | None] = mapped_column(String(512))

    status: Mapped[ImageStatus] = mapped_column(Enum(ImageStatus))
    status_message: Mapped[str | None] = mapped_column(String(512))
    format: Mapped[ImageFormat] = mapped_column(Enum(ImageFormat))
    # Relationship
    samples: Mapped[set[DatabaseSample]] = relationship(
        "DatabaseSample", secondary=sample_to_image, back_populates="images"
    )
    annotations: Mapped[set[DatabaseAnnotation]] = relationship(
        DatabaseAnnotation,
        back_populates="image",
        foreign_keys=[DatabaseAnnotation.image_uid],
    )
    observations: Mapped[set[DatabaseObservation]] = relationship(
        DatabaseObservation,
        back_populates="image",
        foreign_keys=[DatabaseObservation.image_uid],
    )
    files: Mapped[set[DatabaseImageFile]] = relationship(
        DatabaseImageFile,
        back_populates="image",
        foreign_keys=[DatabaseImageFile.image_uid],
        cascade="all, delete-orphan",
    )
    __mapper_args__ = {
        "polymorphic_identity": ItemValueType.IMAGE,
    }
    __tablename__ = "image"

    def __init__(
        self,
        dataset_uid: UUID,
        batch_uid: UUID | None,
        schema_uid: UUID,
        identifier: str,
        format: ImageFormat,
        samples: DatabaseSample | Iterable[DatabaseSample] | None = None,
        attributes: list[DatabaseAttribute] | None = None,
        private_attributes: list[DatabaseAttribute] | None = None,
        tags: list[DatabaseTag] | None = None,
        comment: str | None = None,
        name: str | None = None,
        pseudonym: str | None = None,
        external_identifier: str | None = None,
        selected: bool = True,
        folder_path: str | None = None,
        thumbnail_path: str | None = None,
        uid: UUID | None = None,
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
            and self.valid_pseudonym
            and not self.failed
        )

    @valid.inplace.expression
    @classmethod
    def _valid_expression(cls):
        return and_(
            cls.valid_attributes,
            cls.valid_relations,
            cls.valid_pseudonym,
            cls.status.notin_(
                [
                    ImageStatus.DOWNLOADING_FAILED,
                    ImageStatus.PRE_PROCESSING_FAILED,
                    ImageStatus.POST_PROCESSING_FAILED,
                ]
            ),
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
    def post_processing_failed(self) -> bool:
        return self.status == ImageStatus.POST_PROCESSING_FAILED

    @hybrid_property
    def post_processed(self) -> bool:
        return self.status == ImageStatus.POST_PROCESSED

    @hybrid_property
    def storing(self) -> bool:
        return self.status == ImageStatus.STORING

    @hybrid_property
    def stored(self) -> bool:
        return self.status == ImageStatus.STORED

    @hybrid_property
    def storing_failed(self) -> bool:
        return self.status == ImageStatus.STORING_FAILED

    @hybrid_property
    def processed(self) -> bool:
        """Return True if the image folder holds post-processed image data.

        True from the image being post-processed and onwards, as storing it moves
        the folder but does not change what it holds.
        """
        return self.post_processed or self.storing or self.stored

    @hybrid_property
    def failed(self) -> bool:
        return (
            self.downloading_failed
            or self.pre_processing_failed
            or self.post_processing_failed
            or self.storing_failed
        )

    @property
    def model(self) -> Image:
        samples: dict[UUID, list[UUID]] = defaultdict(list)
        for sample in self.samples:
            if sample.selected:
                samples[sample.schema_uid].append(sample.uid)
        annotations: dict[UUID, list[UUID]] = defaultdict(list)
        for annotation in self.annotations:
            if annotation.selected:
                annotations[annotation.schema_uid].append(annotation.uid)
        observations: dict[UUID, list[UUID]] = defaultdict(list)
        for observation in self.observations:
            if observation.selected:
                observations[observation.schema_uid].append(observation.uid)
        return Image(
            uid=self.uid,
            identifier=self.identifier,
            name=self.name,
            pseudonym=self.pseudonym,
            selected=self.selected,
            valid=(
                self.valid_attributes
                and self.valid_relations
                and self.valid_pseudonym
                and not self.failed
            ),
            valid_attributes=self.valid_attributes,
            valid_relations=self.valid_relations,
            valid_pseudonym=self.valid_pseudonym,
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

    def set_status_message(self, message: str | None) -> None:
        """Set ``status_message``, trimmed to the column width.

        Exception text recorded on a phase failure can exceed the column
        and would otherwise raise on flush, masking the original failure.
        Keep the leading characters where the root cause sits and mark the
        cut.
        """
        max_length = 512  # width of the status_message column
        if message is not None and len(message) > max_length:
            marker = "… [truncated]"
            message = message[: max_length - len(marker)] + marker
        self.status_message = message

    def set_as_downloading(self):
        if not self.not_started:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.NOT_STARTED} image as "
                f"{ImageStatus.DOWNLOADING}, was {self.status}."
            )
        self.status = ImageStatus.DOWNLOADING

    def reset_as_not_started(self):
        if not (self.downloading_failed or self.downloading):
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.DOWNLOADING_FAILED} or "
                f"{ImageStatus.DOWNLOADING} image as "
                f"{ImageStatus.NOT_STARTED}, was {self.status}."
            )
        self.status = ImageStatus.NOT_STARTED

    def set_as_downloading_failed(self):
        if not self.downloading:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.DOWNLOADING} image as "
                f"{ImageStatus.DOWNLOADING_FAILED}, was {self.status}."
            )
        self.status = ImageStatus.DOWNLOADING_FAILED

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
        if not (self.pre_processing_failed or self.pre_processing):
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.PRE_PROCESSING_FAILED} or "
                f"{ImageStatus.PRE_PROCESSING} image as "
                f"{ImageStatus.DOWNLOADED}, was {self.status}."
            )
        self.status = ImageStatus.DOWNLOADED

    def reset_as_pre_processed(self):
        if not (self.post_processing_failed or self.post_processing):
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.POST_PROCESSING_FAILED} or "
                f"{ImageStatus.POST_PROCESSING} image as "
                f"{ImageStatus.PRE_PROCESSED}, was {self.status}."
            )
        self.status = ImageStatus.PRE_PROCESSED

    def reset_as_post_processed(self):
        if not self.storing_failed:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.STORING_FAILED} image as "
                f"{ImageStatus.POST_PROCESSED}, was {self.status}."
            )
        self.status = ImageStatus.POST_PROCESSED

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

    def set_as_storing(self):
        if not (self.post_processed or self.storing):
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.POST_PROCESSED} image as "
                f"{ImageStatus.STORING}, was {self.status}."
            )
        self.status = ImageStatus.STORING

    def set_as_stored(self):
        if not self.storing:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.STORING} image as "
                f"{ImageStatus.STORED}, was {self.status}."
            )
        self.status = ImageStatus.STORED

    def set_as_storing_failed(self):
        if not self.storing:
            raise NotAllowedActionError(
                f"Can only set {ImageStatus.STORING} image as "
                f"{ImageStatus.STORING_FAILED}, was {self.status}."
            )
        self.status = ImageStatus.STORING_FAILED


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
    children: Mapped[set[DatabaseSample]] = relationship(
        "DatabaseSample",
        secondary=sample_to_sample,
        primaryjoin=(uid == sample_to_sample.c.parent_uid),
        secondaryjoin=(uid == sample_to_sample.c.child_uid),
        back_populates="parents",
        cascade="all, delete",
    )
    parents: Mapped[set[DatabaseSample]] = relationship(
        "DatabaseSample",
        secondary=sample_to_sample,
        primaryjoin=(uid == sample_to_sample.c.child_uid),
        secondaryjoin=(uid == sample_to_sample.c.parent_uid),
        back_populates="children",
    )
    images: Mapped[set[DatabaseImage]] = relationship(
        DatabaseImage, secondary=DatabaseImage.sample_to_image, back_populates="samples"
    )
    observations: Mapped[set[DatabaseObservation]] = relationship(
        DatabaseObservation,
        back_populates="sample",
        foreign_keys=[DatabaseObservation.sample_uid],
    )
    __mapper_args__ = {
        "polymorphic_identity": ItemValueType.SAMPLE,
    }
    __tablename__ = "sample"

    def __init__(
        self,
        dataset_uid: UUID,
        batch_uid: UUID | None,
        schema_uid: UUID,
        identifier: str,
        parents: DatabaseSample | Iterable[DatabaseSample] | None = None,
        children: DatabaseSample | Iterable[DatabaseSample] | None = None,
        attributes: list[DatabaseAttribute] | None = None,
        private_attributes: list[DatabaseAttribute] | None = None,
        tags: list[DatabaseTag] | None = None,
        comment: str | None = None,
        name: str | None = None,
        external_identifier: str | None = None,
        pseudonym: str | None = None,
        selected: bool = True,
        uid: UUID | None = None,
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
            if child.selected:
                children[child.schema_uid].append(child.uid)
        parents = defaultdict(list)
        for parent in self.parents:
            if parent.selected:
                parents[parent.schema_uid].append(parent.uid)
        images = defaultdict(list)
        for image in self.images:
            if image.selected:
                images[image.schema_uid].append(image.uid)
        observations = defaultdict(list)
        for observation in self.observations:
            if observation.selected:
                observations[observation.schema_uid].append(observation.uid)
        return Sample(
            uid=self.uid,
            identifier=self.identifier,
            name=self.name,
            pseudonym=self.pseudonym,
            selected=self.selected,
            valid=(
                self.valid_attributes and self.valid_relations and self.valid_pseudonym
            ),
            valid_attributes=self.valid_attributes,
            valid_relations=self.valid_relations,
            valid_pseudonym=self.valid_pseudonym,
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
