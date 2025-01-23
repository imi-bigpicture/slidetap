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

import datetime
from typing import Any, Dict, Iterable, List, Optional
from uuid import UUID, uuid4

from flask import current_app
from sqlalchemy import Uuid, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, attribute_keyed_dict

from slidetap.database.attribute import DatabaseAttribute
from slidetap.database.db import DbBase, db
from slidetap.model import (
    Batch,
    BatchStatus,
    Dataset,
    DatasetSchema,
    Project,
    ProjectSchema,
    ProjectStatus,
)


class DatabaseProject(DbBase):
    """
    A project represents the work of collecting, processing, and curating metadata and
    images in batches to create a dataset.
    """

    uid: Mapped[UUID] = db.Column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = db.Column(db.String(128))
    status: Mapped[ProjectStatus] = db.Column(db.Enum(ProjectStatus))
    valid_attributes: Mapped[bool] = db.Column(db.Boolean)
    locked: Mapped[bool] = db.Column(db.Boolean, default=False)
    root_schema_uid: Mapped[UUID] = db.Column(Uuid)
    schema_uid: Mapped[UUID] = db.Column(Uuid, index=True)
    default_batch_uid: Mapped[UUID] = db.Column(Uuid)
    created: Mapped[datetime.datetime] = db.Column(db.DateTime)

    # Relations
    attributes: Mapped[Dict[str, DatabaseAttribute[Any, Any]]] = db.relationship(
        DatabaseAttribute,
        collection_class=attribute_keyed_dict("tag"),
        cascade="all, delete-orphan",
    )  # type: ignore
    dataset: Mapped["DatabaseDataset"] = db.relationship(
        "DatabaseDataset",
        back_populates="project",
        cascade="all, delete-orphan",
        single_parent=True,
    )  # type: ignore
    batches: Mapped[List["DatabaseBatch"]] = db.relationship(
        "DatabaseBatch",
        back_populates="project",
        cascade="all, delete-orphan",
    )  # type: ignore

    # For relations
    dataset_uid: Mapped[UUID] = db.Column(Uuid, db.ForeignKey("dataset.uid"))

    __tablename__ = "project"

    def __init__(
        self,
        name: str,
        root_schema_uid: UUID,
        schema_uid: UUID,
        dataset_uid: UUID,
        created: datetime.datetime,
        attributes: Optional[Dict[str, DatabaseAttribute]] = None,
        uid: Optional[UUID] = None,
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
        else:
            attributes = {
                attribute.tag: attribute
                for attribute in attributes.values()
                if attribute is not None
            }
        super().__init__(
            name=name,
            root_schema_uid=root_schema_uid,
            schema_uid=schema_uid,
            dataset_uid=dataset_uid,
            created=created,
            attributes=attributes,
            status=ProjectStatus.IN_PROGRESS,
            uid=uid if uid != UUID(int=0) else uuid4(),
            add=add,
            commit=commit,
        )

    def __str__(self) -> str:
        return f"Project id: {self.uid}, name {self.name}, " f"status: {self.status}."

    @property
    def attribute_tags(self) -> Iterable[str]:
        return db.session.scalars(
            select(DatabaseAttribute.tag).where(
                DatabaseAttribute.project_uid == self.uid
            )
        ).all()

    def get_attribute(self, tag: str) -> DatabaseAttribute:
        return db.session.scalars(
            select(DatabaseAttribute).filter_by(project_uid=self.uid, tag=tag)
        ).one()

    @hybrid_property
    def in_progress(self) -> bool:
        """Return True if project have status 'IN_PROGRESS'."""
        return self.status == ProjectStatus.IN_PROGRESS

    @hybrid_property
    def completed(self) -> bool:
        """Return True if project have status 'COMPLETED'."""
        return self.status == ProjectStatus.COMPLETED

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
    def valid(self) -> bool:
        if not self.valid_attributes:
            current_app.logger.info(
                f"Project {self.uid} is not valid as attributes are not valid."
            )
            return False
        return True

    @property
    def model(self) -> Project:
        return Project(
            uid=self.uid,
            name=self.name,
            status=self.status,
            valid_attributes=self.valid_attributes,
            attributes={
                attribute.tag: attribute.model for attribute in self.attributes.values()
            },
            root_schema_uid=self.root_schema_uid,
            schema_uid=self.schema_uid,
            dataset_uid=self.dataset_uid,
            created=self.created,
        )

    @classmethod
    def get_or_create_from_model(
        cls, project: Project, schema: ProjectSchema
    ) -> "DatabaseProject":
        """Get or create project from model.

        Parameters
        ----------
        project: Project
            Project to get or create.

        Returns
        ----------
        Project
            Project with id.
        """
        existing_project = db.session.get(cls, project.uid)
        if existing_project is not None:
            return existing_project
        return cls(
            name=project.name,
            root_schema_uid=project.root_schema_uid,
            schema_uid=project.schema_uid,
            dataset_uid=project.dataset_uid,
            created=project.created,
            attributes={
                key: DatabaseAttribute.get_or_create_from_model(
                    attribute, schema.attributes[key], add=True, commit=False
                )
                for key, attribute in project.attributes.items()
            },
            uid=project.uid,
            add=True,
            commit=True,
        )


class DatabaseDataset(DbBase):
    """A dataset represents the collection of finalized metadata and images."""

    name: Mapped[str] = db.Column(db.String(128))
    uid: Mapped[UUID] = db.Column(Uuid, primary_key=True, default=uuid4)
    valid_attributes: Mapped[bool] = db.Column(db.Boolean)
    valid_items: Mapped[bool] = db.Column(db.Boolean)
    schema_uid: Mapped[UUID] = db.Column(Uuid, index=True)

    # Relations
    project: Mapped[Optional[DatabaseProject]] = db.relationship(
        DatabaseProject, back_populates="dataset"
    )  # type: ignore
    attributes: Mapped[Dict[str, DatabaseAttribute[Any, Any]]] = db.relationship(
        DatabaseAttribute,
        collection_class=attribute_keyed_dict("tag"),
        cascade="all, delete-orphan",
    )  # type: ignore

    # For relations
    __tablename__ = "dataset"

    def __init__(
        self,
        name: str,
        schema_uid: UUID,
        uid: Optional[UUID] = None,
        attributes: Optional[Dict[str, DatabaseAttribute]] = None,
        add: bool = True,
        commit: bool = True,
    ):
        """Create a dataset.

        Parameters
        ----------
        name: str
            Name of project.

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
            name=name,
            schema_uid=schema_uid,
            uid=uid if uid != UUID(int=0) else uuid4(),
            attributes=attributes,
            add=add,
            commit=commit,
        )

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def get_all(cls) -> Iterable["DatabaseDataset"]:
        query = select(cls)
        return db.session.scalars(query)

    @property
    def model(self) -> Dataset:
        return Dataset(
            uid=self.uid,
            name=self.name,
            schema_uid=self.schema_uid,
            valid_attributes=self.valid_attributes,
            attributes={
                attribute.tag: attribute.model for attribute in self.attributes.values()
            },
        )

    @property
    def attribute_tags(self) -> Iterable[str]:
        return db.session.scalars(
            select(DatabaseAttribute.tag).where(
                DatabaseAttribute.project_uid == self.uid
            )
        ).all()

    def get_attribute(self, tag: str) -> DatabaseAttribute:
        return db.session.scalars(
            select(DatabaseAttribute).filter_by(project_uid=self.uid, tag=tag)
        ).one()

    @classmethod
    def get_or_create_from_model(
        cls, dataset: Dataset, schema: DatasetSchema
    ) -> "DatabaseDataset":
        """Get or create project from model.

        Parameters
        ----------
        project: Project
            Project to get or create.

        Returns
        ----------
        Project
            Project with id.
        """
        existing = db.session.get(cls, dataset.uid)
        if existing is not None:
            return existing
        return cls(
            name=dataset.name,
            schema_uid=dataset.schema_uid,
            uid=dataset.uid,
            attributes={
                key: DatabaseAttribute.get_or_create_from_model(
                    attribute, schema.attributes[key], add=True, commit=False
                )
                for key, attribute in dataset.attributes.items()
            },
        )

    def set_attributes(
        self, attributes: Dict[str, DatabaseAttribute], commit: bool = True
    ) -> None:
        self.attributes = attributes
        if commit:
            db.session.commit()

    def update_attributes(
        self, attributes: Dict[str, DatabaseAttribute], commit: bool = True
    ) -> None:
        self.attributes.update(attributes)
        if commit:
            db.session.commit()


class DatabaseBatch(DbBase):
    """A batch is a collection of items in preparation for a project."""

    name: Mapped[str] = db.Column(db.String(128))
    uid: Mapped[UUID] = db.Column(Uuid, primary_key=True, default=uuid4)
    status: Mapped[BatchStatus] = db.Column(db.Enum(BatchStatus))
    created: Mapped[datetime.datetime] = db.Column(db.DateTime)

    # Relations
    project: Mapped[DatabaseProject] = db.relationship(
        DatabaseProject,
        back_populates="batches",
    )  # type: ignore

    # For relations
    project_uid: Mapped[UUID] = db.Column(Uuid, db.ForeignKey("project.uid"))

    # For relations
    __tablename__ = "batch"

    def __init__(
        self,
        name: str,
        project_uid: UUID,
        created: datetime.datetime,
        uid: Optional[UUID] = None,
        add: bool = True,
        commit: bool = True,
    ):
        """Create a dataset.

        Parameters
        ----------
        name: str
            Name of project.

        """
        super().__init__(
            name=name,
            status=BatchStatus.INITIALIZED,
            project_uid=project_uid,
            created=created,
            uid=uid if uid != UUID(int=0) else uuid4(),
            add=add,
            commit=commit,
        )

    @hybrid_property
    def initialized(self) -> bool:
        """Return True if project have status 'INITIALIZED'."""
        return self.status == BatchStatus.INITIALIZED

    @hybrid_property
    def metadata_searching(self) -> bool:
        """Return True if project have status 'METADATA_SEARCHING'."""
        return self.status == BatchStatus.METADATA_SEARCHING

    @hybrid_property
    def metadata_search_complete(self) -> bool:
        """Return True if project have status 'SEARCH_COMPLETE'."""
        return self.status == BatchStatus.METADATA_SEARCH_COMPLETE

    @hybrid_property
    def image_pre_processing(self) -> bool:
        """Return True if project have status 'IMAGE_PRE_PROCESSING'."""
        return self.status == BatchStatus.IMAGE_PRE_PROCESSING

    @hybrid_property
    def image_pre_processing_complete(self) -> bool:
        """Return True if project have status 'IMAGE_PRE_PROCESSING_COMPLETE'."""
        return self.status == BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE

    @hybrid_property
    def image_post_processing(self) -> bool:
        """Return True if project have status 'IMAGE_POST_PROCESSING'."""
        return self.status == BatchStatus.IMAGE_POST_PROCESSING

    @hybrid_property
    def image_post_processing_complete(self) -> bool:
        """Return True if project have status 'IMAGE_POST_PROCESSING_COMPLETE'."""
        return self.status == BatchStatus.IMAGE_POST_PROCESSING_COMPLETE

    @hybrid_property
    def failed(self) -> bool:
        """Return True if project have status 'FAILED'."""
        return self.status == BatchStatus.FAILED

    @hybrid_property
    def deleted(self) -> bool:
        return self.status == BatchStatus.DELETED

    @hybrid_property
    def completed(self) -> bool:
        return self.status == BatchStatus.COMPLETED

    @classmethod
    def get_for_project(
        cls, project: DatabaseProject, valid: Optional[bool] = None
    ) -> Iterable["DatabaseBatch"]:
        """Return all batches for a dataset.

        Parameters
        ----------
        dataset: Dataset
            Dataset to get batches for.
        valid: Optional[bool]
            If set, only return batches that are valid.

        Returns
        ----------
        List[Batch]
            List of batches.
        """
        query = select(cls).where(cls.project_uid == project.uid)
        if valid is not None:
            query = query.filter_by(valid=valid)
        return db.session.scalars(query)

    @classmethod
    def get_all(
        cls, project_uid: Optional[UUID] = None, status: Optional[BatchStatus] = None
    ) -> Iterable["DatabaseBatch"]:
        """Return all batches.

        Returns
        ----------
        List[Batch]
            List of batches.
        """
        query = select(cls)
        if project_uid is not None:
            query = query.where(cls.project_uid == project_uid)
        if status is not None:
            query = query.where(cls.status == status)
        return db.session.scalars(query)

    @property
    def model(self) -> Batch:
        return Batch(
            uid=self.uid,
            name=self.name,
            status=self.status,
            project_uid=self.project_uid,
            is_default=self.project.default_batch_uid == self.uid,
            created=self.created,
        )

    @classmethod
    def get_or_create_from_model(cls, batch: Batch) -> "DatabaseBatch":
        """Get or create project from model.

        Parameters
        ----------
        project: Project
            Project to get or create.

        Returns
        ----------
        Project
            Project with id.
        """
        existing = db.session.get(cls, batch.uid)
        if existing is not None:
            return existing
        return cls(
            name=batch.name,
            project_uid=batch.project_uid,
            created=batch.created,
            uid=batch.uid,
        )
