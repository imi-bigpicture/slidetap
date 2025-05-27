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
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String, Table, Uuid
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, attribute_keyed_dict, mapped_column, relationship

from slidetap.database.attribute import DatabaseAttribute
from slidetap.database.db import Base
from slidetap.database.mapper import DatabaseMapper
from slidetap.model import (
    Batch,
    BatchStatus,
    Dataset,
    Project,
    ProjectStatus,
)


class DatabaseProject(Base):
    """
    A project represents the work of collecting, processing, and curating metadata and
    images in batches to create a dataset.
    """

    # table for mapping many-to-many projects and mappers
    mapper_to_project = Table(
        "mapper_to_project",
        Base.metadata,
        Column(
            "mapper_uid",
            Uuid,
            ForeignKey("mapper.uid"),
            primary_key=True,
        ),
        Column(
            "project_uid",
            Uuid,
            ForeignKey("project.uid"),
            primary_key=True,
        ),
    )

    uid: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(128))
    status: Mapped[ProjectStatus] = mapped_column(Enum(ProjectStatus))
    valid_attributes: Mapped[Optional[bool]] = mapped_column(Boolean)
    locked: Mapped[bool] = mapped_column(Boolean, default=False)
    root_schema_uid: Mapped[UUID] = mapped_column(Uuid)
    schema_uid: Mapped[UUID] = mapped_column(Uuid, index=True)
    default_batch_uid: Mapped[Optional[UUID]] = mapped_column(Uuid)
    created: Mapped[datetime.datetime] = mapped_column(DateTime)

    # Relations
    attributes: Mapped[Dict[str, DatabaseAttribute[Any, Any]]] = relationship(
        DatabaseAttribute,
        collection_class=attribute_keyed_dict("tag"),
        cascade="all, delete-orphan",
    )  # type: ignore
    dataset: Mapped["DatabaseDataset"] = relationship(
        "DatabaseDataset",
        back_populates="project",
        cascade="all, delete-orphan",
        single_parent=True,
    )  # type: ignore
    batches: Mapped[List["DatabaseBatch"]] = relationship(
        "DatabaseBatch",
        back_populates="project",
        cascade="all, delete-orphan",
    )  # type: ignore
    mappers: Mapped[List[DatabaseMapper]] = relationship(
        "DatabaseMapper",
        secondary=mapper_to_project,
    )  # type: ignore

    # For relations
    dataset_uid: Mapped[UUID] = mapped_column(Uuid, ForeignKey("dataset.uid"))

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
            uid=uid if (uid != UUID(int=0) and uid) else uuid4(),
        )

    def __str__(self) -> str:
        return f"Project id: {self.uid}, name {self.name}, " f"status: {self.status}."

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
            logging.info(
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
            mapper_uids=[mapper.uid for mapper in self.mappers],
            root_schema_uid=self.root_schema_uid,
            schema_uid=self.schema_uid,
            dataset_uid=self.dataset_uid,
            created=self.created,
        )


class DatabaseDataset(Base):
    """A dataset represents the collection of finalized metadata and images."""

    name: Mapped[str] = mapped_column(String(128))
    uid: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    valid_attributes: Mapped[Optional[bool]] = mapped_column(Boolean)
    valid_items: Mapped[Optional[bool]] = mapped_column(Boolean)
    schema_uid: Mapped[UUID] = mapped_column(Uuid, index=True)

    # Relations
    project: Mapped[Optional[DatabaseProject]] = relationship(
        DatabaseProject, back_populates="dataset"
    )  # type: ignore
    attributes: Mapped[Dict[str, DatabaseAttribute[Any, Any]]] = relationship(
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
            uid=uid if (uid != UUID(int=0) and uid) else uuid4(),
            attributes=attributes,
        )

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


class DatabaseBatch(Base):
    """A batch is a collection of items in preparation for a project."""

    name: Mapped[str] = mapped_column(String(128))
    uid: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    status: Mapped[BatchStatus] = mapped_column(Enum(BatchStatus))
    created: Mapped[datetime.datetime] = mapped_column(DateTime)

    # Relations
    project: Mapped[DatabaseProject] = relationship(
        DatabaseProject,
        back_populates="batches",
    )  # type: ignore

    # For relations
    project_uid: Mapped[UUID] = mapped_column(Uuid, ForeignKey("project.uid"))

    # For relations
    __tablename__ = "batch"

    def __init__(
        self,
        name: str,
        project_uid: UUID,
        created: datetime.datetime,
        uid: Optional[UUID] = None,
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
            uid=uid if (uid != UUID(int=0) and uid) else uuid4(),
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
