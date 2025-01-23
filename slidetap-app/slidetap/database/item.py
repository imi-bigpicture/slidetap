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
from typing import (
    Any,
    Dict,
    Generic,
    Iterable,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)
from uuid import UUID, uuid4

from sqlalchemy import Uuid, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, attribute_keyed_dict, mapped_column

from slidetap.database.attribute import DatabaseAttribute
from slidetap.database.db import DbBase, NotAllowedActionError, db
from slidetap.database.project import DatabaseBatch, DatabaseDataset
from slidetap.model import (
    Annotation,
    Image,
    ImageFile,
    ImageStatus,
    Item,
    ItemType,
    ItemValueType,
    Observation,
    Sample,
)
from slidetap.model.item_reference import ItemReference
from slidetap.model.schema.item_schema import ItemSchema

DatabaseItemType = TypeVar("DatabaseItemType", bound="DatabaseItem")


class DatabaseItem(DbBase, Generic[ItemType]):
    """Base class for an metadata item."""

    uid: Mapped[UUID] = db.Column(Uuid, primary_key=True, default=uuid4)
    identifier: Mapped[str] = db.Column(db.String(128))
    name: Mapped[Optional[str]] = db.Column(db.String(128))
    pseudonym: Mapped[Optional[str]] = db.Column(db.String(128))
    selected: Mapped[bool] = db.Column(db.Boolean, default=True)
    valid_attributes: Mapped[bool] = db.Column(db.Boolean)
    valid_relations: Mapped[bool] = db.Column(db.Boolean)
    item_value_type: Mapped[ItemValueType] = db.Column(
        db.Enum(ItemValueType), index=True
    )
    locked: Mapped[bool] = db.Column(db.Boolean, default=False)
    schema_uid: Mapped[UUID] = db.Column(Uuid, index=True)

    # Relations
    attributes: Mapped[Dict[str, DatabaseAttribute[Any, Any]]] = db.relationship(
        DatabaseAttribute,
        collection_class=attribute_keyed_dict("tag"),
        cascade="all, delete-orphan",
    )  # type: ignore
    dataset: Mapped[DatabaseDataset] = db.relationship(DatabaseDataset)  # type: ignore
    batch: Mapped[Optional[DatabaseBatch]] = db.relationship(DatabaseBatch)  # type: ignore

    # For relations

    dataset_uid: Mapped[UUID] = db.Column(
        Uuid, db.ForeignKey("dataset.uid"), index=True
    )
    batch_uid: Mapped[UUID] = db.Column(Uuid, db.ForeignKey("batch.uid"), index=True)

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
            dataset_uid=dataset_uid,
            batch_uid=batch_uid,
            schema_uid=schema_uid,
            identifier=identifier,
            name=name,
            pseudonym=pseudonym,
            attributes=attributes,
            selected=selected,
            uid=uid if uid != UUID(int=0) else None,
        )

    @property
    def attribute_tags(self) -> Iterable[str]:
        return db.session.scalars(
            select(DatabaseAttribute.tag).filter_by(item_uid=self.uid)
        ).all()

    def get_attribute(self, tag: str) -> DatabaseAttribute:
        return db.session.scalars(
            select(DatabaseAttribute).filter_by(item_uid=self.uid, tag=tag)
        ).one()

    def get_optional_attribute(self, tag: str) -> Optional[DatabaseAttribute]:
        return db.session.scalars(
            select(DatabaseAttribute).filter_by(item_uid=self.uid, tag=tag)
        ).one_or_none()

    @classmethod
    def get_or_create_from_model(
        cls,
        model: Item,
        schema: ItemSchema,
        append_relations: bool = False,
        add: bool = True,
        commit: bool = True,
    ) -> DatabaseItem:
        if isinstance(model, Annotation):
            return DatabaseAnnotation.get_or_create_from_model(
                model, schema, append_relations, add, commit
            )
        if isinstance(model, Image):
            return DatabaseImage.get_or_create_from_model(
                model, schema, append_relations, add, commit
            )
        if isinstance(model, Observation):
            return DatabaseObservation.get_or_create_from_model(
                model, schema, append_relations, add, commit
            )
        if isinstance(model, Sample):
            return DatabaseSample.get_or_create_from_model(
                model, schema, append_relations, add, commit
            )
        raise ValueError(f"Unknown model type {model}.")

    @hybrid_property
    def valid(self) -> bool:
        return self.valid_attributes and self.valid_relations

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


class DatabaseObservation(DatabaseItem[Observation]):
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
        attributes: Optional[Dict[str, DatabaseAttribute]] = None,
        name: Optional[str] = None,
        pseudonym: Optional[str] = None,
        selected: bool = True,
        uid: Optional[UUID] = None,
        add: bool = True,
        commit: bool = True,
    ):
        super().__init__(
            dataset_uid=dataset_uid,
            batch_uid=batch_uid,
            schema_uid=schema_uid,
            identifier=identifier,
            name=name,
            pseudonym=pseudonym,
            selected=selected,
            attributes=attributes,
            add=add,
            uid=uid,
        )
        if isinstance(item, DatabaseImage):
            self.image = item
        elif isinstance(item, DatabaseSample):
            self.sample = item
        elif isinstance(item, DatabaseAnnotation):
            self.annotation = item
        if commit:
            db.session.commit()

    @classmethod
    def get_or_create_from_model(
        cls,
        model: Observation,
        schema: ItemSchema,
        append_relations: bool = False,
        add: bool = True,
        commit: bool = True,
    ) -> "DatabaseObservation":
        existing = db.session.get(cls, model.uid)
        if existing is not None:
            return existing
        if append_relations:
            if model.sample is not None:
                item = DatabaseSample.get(model.sample)
            elif model.image is not None:
                item = DatabaseImage.get(model.image)
            elif model.annotation is not None:
                item = DatabaseAnnotation.get(model.annotation)
            else:
                item = None
        else:
            item = None
        attributes = {
            tag: DatabaseAttribute.get_or_create_from_model(
                attribute, schema.attributes[tag], add=add, commit=False
            )
            for tag, attribute in model.attributes.items()
        }
        return cls(
            dataset_uid=model.dataset_uid,
            batch_uid=model.batch_uid,
            schema_uid=model.schema_uid,
            identifier=model.identifier,
            item=item,
            attributes=attributes,
            name=model.name,
            pseudonym=model.pseudonym,
            selected=model.selected,
            uid=model.uid,
            commit=commit,
            add=add,
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
                attribute.tag: attribute.model for attribute in self.attributes.values()
            },
            dataset_uid=self.dataset_uid,
            schema_uid=self.schema_uid,
            batch_uid=self.batch_uid,
            sample=self.sample_uid,
            image=self.image_uid,
            annotation=self.annotation_uid,
        )


class DatabaseAnnotation(DatabaseItem[Annotation]):
    """An annotation item. Is related to an image."""

    uid: Mapped[UUID] = mapped_column(
        db.ForeignKey("item.uid", ondelete="CASCADE"), primary_key=True
    )

    # For relations
    image_uid: Mapped[UUID] = mapped_column(db.ForeignKey("image.uid"))

    # Relationships
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
        dataset_uid: UUID,
        batch_uid: Optional[UUID],
        schema_uid: UUID,
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
            dataset_uid=dataset_uid,
            batch_uid=batch_uid,
            schema_uid=schema_uid,
            identifier=identifier,
            attributes=attributes,
            name=name,
            pseudonym=pseudonym,
            selected=selected,
            uid=uid,
            add=add,
        )
        self.image = image
        if commit:
            db.session.commit()

    @classmethod
    def get_or_create_from_model(
        cls,
        model: Annotation,
        schema: ItemSchema,
        append_relations: bool = False,
        add: bool = True,
        commit: bool = True,
    ) -> "DatabaseAnnotation":
        existing = db.session.get(cls, model.uid)
        if existing is not None:
            return existing
        if append_relations and model.image is not None:
            image = DatabaseImage.get(model.image)
        else:
            image = None
        attributes = {
            tag: DatabaseAttribute.get_or_create_from_model(
                attribute, schema.attributes[tag], add=add, commit=False
            )
            for tag, attribute in model.attributes.items()
        }
        return cls(
            dataset_uid=model.dataset_uid,
            batch_uid=model.batch_uid,
            schema_uid=model.schema_uid,
            identifier=model.identifier,
            image=image,
            attributes=attributes,
            name=model.name,
            pseudonym=model.pseudonym,
            selected=model.selected,
            uid=model.uid,
            add=add,
            commit=commit,
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
                attribute.tag: attribute.model for attribute in self.attributes.values()
            },
            dataset_uid=self.dataset_uid,
            schema_uid=self.schema_uid,
            batch_uid=self.batch_uid,
            image=self.image.uid if self.image is not None else None,
            obseration=[observation.uid for observation in self.observations],
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


class DatabaseImage(DatabaseItem[Image]):
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

    folder_path: Mapped[Optional[str]] = db.Column(db.String(512))
    thumbnail_path: Mapped[Optional[str]] = db.Column(db.String(512))

    status: Mapped[ImageStatus] = db.Column(db.Enum(ImageStatus))
    status_message: Mapped[Optional[str]] = db.Column(db.String(512))
    # Relationship
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
        dataset_uid: UUID,
        batch_uid: Optional[UUID],
        schema_uid: UUID,
        identifier: str,
        samples: Optional[Union["DatabaseSample", Iterable["DatabaseSample"]]] = None,
        attributes: Optional[Dict[str, DatabaseAttribute]] = None,
        name: Optional[str] = None,
        pseudonym: Optional[str] = None,
        external_identifier: Optional[str] = None,
        selected: bool = True,
        files: Optional[List[DatabaseImageFile]] = None,
        folder_path: Optional[str] = None,
        thumbnail_path: Optional[str] = None,
        uid: Optional[UUID] = None,
        add: bool = True,
        commit: bool = True,
    ):
        self.status = ImageStatus.NOT_STARTED
        self.external_identifier = external_identifier
        super().__init__(
            dataset_uid=dataset_uid,
            batch_uid=batch_uid,
            schema_uid=schema_uid,
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
            self.samples = list(samples)
        if files is not None:
            self.files = files
        self.folder_path = folder_path
        self.thumbnail_path = thumbnail_path
        if commit:
            db.session.commit()

    @classmethod
    def get_or_create_from_model(
        cls,
        model: Image,
        schema: ItemSchema,
        append_relations: bool = False,
        add: bool = True,
        commit: bool = True,
    ) -> "DatabaseImage":
        existing = db.session.get(cls, model.uid)
        if existing is not None:
            return existing
        if append_relations and model.samples is not None:
            samples = (DatabaseSample.get(sample) for sample in model.samples)
        else:
            samples = None

        attributes = {
            tag: DatabaseAttribute.get_or_create_from_model(
                attribute, schema.attributes[tag], add=add, commit=False
            )
            for tag, attribute in model.attributes.items()
        }
        return cls(
            dataset_uid=model.dataset_uid,
            batch_uid=model.batch_uid,
            schema_uid=model.schema_uid,
            identifier=model.identifier,
            samples=samples,
            attributes=attributes,
            name=model.name,
            pseudonym=model.pseudonym,
            external_identifier=model.external_identifier,
            selected=model.selected,
            uid=model.uid,
            add=add,
            commit=commit,
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
                attribute.tag: attribute.model for attribute in self.attributes.values()
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
            samples=[sample.uid for sample in self.samples],
            annotations=[annotation.uid for annotation in self.annotations],
            observations=[observation.uid for observation in self.observations],
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

    @classmethod
    def get_first_image_for_batch(
        cls,
        batch_uid: UUID,
        include_status: Iterable[ImageStatus] = [],
        exclude_status: Iterable[ImageStatus] = [],
        selected: Optional[bool] = None,
    ) -> Optional[DatabaseImage]:
        query = select(DatabaseImage).filter(DatabaseImage.batch_uid == batch_uid)
        for item in include_status:
            query = query.filter(DatabaseImage.status == item)
        for item in exclude_status:
            query = query.filter(DatabaseImage.status != item)
        if selected is not None:
            query = query.filter(DatabaseImage.selected == selected)
        return db.session.scalars(query).first()


class DatabaseSample(DatabaseItem[Sample]):
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
        attributes: Optional[Dict[str, DatabaseAttribute]] = None,
        name: Optional[str] = None,
        pseudonym: Optional[str] = None,
        selected: bool = True,
        uid: Optional[UUID] = None,
        add: bool = True,
        commit: bool = True,
    ):
        super().__init__(
            dataset_uid=dataset_uid,
            batch_uid=batch_uid,
            schema_uid=schema_uid,
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
            self.parents = list(parents)
        if children is not None:
            if not isinstance(children, Iterable):
                children = [children]
            self.children = list(children)

        if commit:
            db.session.commit()

    @classmethod
    def get_or_create_from_model(
        cls,
        model: Sample,
        schema: ItemSchema,
        append_relations: bool = False,
        add: bool = True,
        commit: bool = True,
    ) -> "DatabaseSample":
        existing = db.session.get(cls, model.uid)
        if existing is not None:
            if append_relations:
                existing_parents = {parent.uid for parent in existing.parents}
                for parent in model.parents:
                    if parent not in existing_parents:
                        existing.parents.append(DatabaseSample.get(parent))
                existing_children = {child.uid for child in existing.children}
                for child in model.children:
                    if child not in existing_children:
                        existing.children.append(DatabaseSample.get(child))
                existing_images = {image.uid for image in existing.images}
                for image in model.images:
                    if image not in existing_images:
                        existing.images.append(DatabaseImage.get(image))
                existing_observations = {
                    observation.uid for observation in existing.observations
                }
                for observation in model.observations:
                    if observation not in existing_observations:
                        existing.observations.append(
                            DatabaseObservation.get(observation)
                        )

            return existing
        if model.parents is not None:
            parents = (DatabaseSample.get(sample) for sample in model.parents)
        else:
            parents = None
        if model.children is not None:
            children = (DatabaseSample.get(sample) for sample in model.children)
        else:
            children = None

        attributes = {
            tag: DatabaseAttribute.get_or_create_from_model(
                attribute, schema.attributes[tag], add=add, commit=False
            )
            for tag, attribute in model.attributes.items()
        }
        return cls(
            dataset_uid=model.dataset_uid,
            batch_uid=model.batch_uid,
            schema_uid=model.schema_uid,
            identifier=model.identifier,
            parents=parents,
            children=children,
            attributes=attributes,
            name=model.name,
            pseudonym=model.pseudonym,
            selected=model.selected,
            uid=model.uid,
            add=add,
            commit=commit,
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
                attribute.tag: attribute.model for attribute in self.attributes.values()
            },
            dataset_uid=self.dataset_uid,
            schema_uid=self.schema_uid,
            batch_uid=self.batch_uid,
            children=[child.uid for child in self.children],
            parents=[parent.uid for parent in self.parents],
            images=[image.uid for image in self.images],
            observations=[observation.uid for observation in self.observations],
        )
