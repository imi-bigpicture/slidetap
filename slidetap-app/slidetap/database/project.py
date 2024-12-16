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

from typing import Any, Dict, Iterable, Optional
from uuid import UUID, uuid4
from xmlrpc.client import boolean

from flask import current_app
from sqlalchemy import Uuid, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, attribute_keyed_dict

from slidetap.database.attribute import DatabaseAttribute
from slidetap.database.db import DbBase, NotAllowedActionError, db

# from slidetap.database.schema.project_schema import DatabaseProjectSchema
from slidetap.model.project import Project
from slidetap.model.project_status import ProjectStatus
from slidetap.model.schema.project_schema import ProjectSchema


class DatabaseProject(DbBase):
    """Represents a project containing samples, images, annotations, and
    observations."""

    uid: Mapped[UUID] = db.Column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = db.Column(db.String(128))
    status: Mapped[ProjectStatus] = db.Column(db.Enum(ProjectStatus))
    valid_items: Mapped[bool] = db.Column(db.Boolean)
    valid_attributes: Mapped[bool] = db.Column(db.Boolean)

    # Relations
    # schema: Mapped[DatabaseProjectSchema] = db.relationship(DatabaseProjectSchema)  # type: ignore
    # Relations
    attributes: Mapped[Dict[str, DatabaseAttribute[Any, Any]]] = db.relationship(
        DatabaseAttribute,
        collection_class=attribute_keyed_dict("tag"),
        cascade="all, delete-orphan",
    )  # type: ignore

    # For relations
    schema_uid: Mapped[UUID] = db.Column(Uuid, index=True)
    __tablename__ = "project"

    def __init__(
        self,
        name: str,
        schema_uid: UUID,
        attributes: Optional[Dict[str, DatabaseAttribute]] = None,
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
            schema_uid=schema_uid,
            attributes=attributes,
            status=ProjectStatus.INITIALIZED,
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

    def iterate_attributes(self) -> Iterable[DatabaseAttribute]:
        return db.session.scalars(
            select(DatabaseAttribute).where(DatabaseAttribute.project_uid == self.uid)
        )

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
    def valid(self) -> bool:
        if not self.valid_attributes:
            current_app.logger.info(
                f"Project {self.uid} is not valid as attributes are not valid."
            )
            return False
        if not self.valid_items:
            current_app.logger.info(
                f"Project {self.uid} is not valid as items are not valid."
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
                attribute.tag: attribute.model
                for attribute in self.iterate_attributes()
            },
            schema_uid=self.schema_uid,
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
            schema_uid=project.schema_uid,
            attributes={
                key: DatabaseAttribute.get_or_create_from_model(
                    attribute, schema.attributes[key]
                )
                for key, attribute in project.attributes.items()
            },
            add=True,
            commit=True,
        )

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

    def delete_project(self) -> bool:
        """Delete project"""

        if (
            not self.initialized
            or self.metadata_searching
            or self.metadata_search_complete
        ):
            return False
        self.status = ProjectStatus.DELETED
        db.session.delete(self)
        db.session.commit()
        return True

    def set_as_searching(self):
        """Set project as 'SEARCHING' if not started."""
        if not self.initialized:
            error = f"Can only set {ProjectStatus.INITIALIZED} project as {ProjectStatus.METADATA_SEARCHING}, was {self.status}"
            current_app.logger.error(error)
            raise NotAllowedActionError(error)
        self.status = ProjectStatus.METADATA_SEARCHING
        current_app.logger.debug(f"Project {self.uid} set as searching.")
        db.session.commit()

    def set_as_search_complete(self):
        """Set project as 'SEARCH_COMPLETE' if not started."""
        if not self.metadata_searching:
            error = (
                f"Can only set {ProjectStatus.METADATA_SEARCHING} project as "
                f"{ProjectStatus.METADATA_SEARCHING}, was {self.status}"
            )
            current_app.logger.error(error)
            raise NotAllowedActionError(error)

        self.status = ProjectStatus.METADATA_SEARCH_COMPLETE
        current_app.logger.debug(f"Project {self.uid} set as {self.status}.")
        db.session.commit()

    def set_as_pre_processing(self):
        """Set project as 'PRE_PROCESSING' if not started."""
        if not self.metadata_search_complete:
            error = (
                f"Can only set {ProjectStatus.METADATA_SEARCH_COMPLETE} project as "
                f"{ProjectStatus.IMAGE_PRE_PROCESSING}, was {self.status}"
            )
            current_app.logger.error(error)
            raise NotAllowedActionError(error)
        self.status = ProjectStatus.IMAGE_PRE_PROCESSING
        current_app.logger.debug(f"Project {self.uid} set as pre-processing.")
        db.session.commit()

    def set_as_pre_processed(self, force: bool = False):
        """Set project as 'PRE_PROCESSED' if not started."""
        if not self.image_pre_processing and not (force and self.image_post_processing):
            error = (
                f"Can only set {ProjectStatus.IMAGE_PRE_PROCESSING} project as "
                f"{ProjectStatus.IMAGE_PRE_PROCESSING_COMPLETE}, was {self.status}"
            )
            current_app.logger.error(error)
            raise NotAllowedActionError(error)
        self.status = ProjectStatus.IMAGE_PRE_PROCESSING_COMPLETE
        current_app.logger.debug(f"Project {self.uid} set as pre-processed.")
        db.session.commit()

    def set_as_post_processing(self):
        """Set project as 'POST_PROCESSING' if not started."""
        if not self.image_pre_processing_complete:
            error = (
                f"Can only set {ProjectStatus.IMAGE_PRE_PROCESSING_COMPLETE} project as "
                f"{ProjectStatus.IMAGE_POST_PROCESSING}, was {self.status}"
            )
            current_app.logger.error(error)
            raise NotAllowedActionError(error)
        self.status = ProjectStatus.IMAGE_POST_PROCESSING
        current_app.logger.debug(f"Project {self.uid} set as post-processing.")
        db.session.commit()

    def set_as_post_processed(self, force: bool = False):
        """Set project as 'POST_PROCESSED' if not started."""
        if not self.image_post_processing and not (force and self.exporting):
            error = (
                f"Can only set {ProjectStatus.IMAGE_POST_PROCESSING} project as "
                f"{ProjectStatus.IMAGE_POST_PROCESSING_COMPLETE}, was {self.status}"
            )
            current_app.logger.error(error)
            raise NotAllowedActionError(error)
        self.status = ProjectStatus.IMAGE_POST_PROCESSING_COMPLETE
        current_app.logger.debug(f"Project {self.uid} set as post-processed.")
        db.session.commit()

    def set_as_exporting(self):
        """Set project as 'EXPORTING' if not started."""
        if not self.image_post_processing_complete:
            error = f"Can only set {ProjectStatus.IMAGE_POST_PROCESSING_COMPLETE} project as {ProjectStatus.EXPORTING}, was {self.status}"
            current_app.logger.error(error)
            raise NotAllowedActionError(error)
        self.status = ProjectStatus.EXPORTING
        current_app.logger.debug(f"Project {self.uid} set as exporting.")
        db.session.commit()

    def set_as_export_complete(self):
        """Set project as 'EXPORT_COMPLETE' if not started."""
        if not self.exporting:
            error = f"Can only set {ProjectStatus.EXPORTING} project as {ProjectStatus.EXPORT_COMPLETE}, was {self.status}"
            current_app.logger.error(error)
            raise NotAllowedActionError(error)
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
