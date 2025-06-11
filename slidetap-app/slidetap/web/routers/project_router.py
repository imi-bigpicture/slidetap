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

"""FastAPI router for handling projects and items in projects."""
import datetime
import logging
from typing import Iterable
from uuid import UUID

from dishka.integrations.fastapi import (
    DishkaRoute,
    FromDishka,
)
from fastapi import APIRouter, Depends, HTTPException

from slidetap.model import Project
from slidetap.model.batch import Batch
from slidetap.model.batch_status import BatchStatus
from slidetap.model.validation import ProjectValidation
from slidetap.services import (
    BatchService,
    DatabaseService,
    DatasetService,
    ProjectService,
    ValidationService,
)
from slidetap.web.routers.login_router import require_login
from slidetap.web.services import (
    MetadataExportService,
    MetadataImportService,
)

project_router = APIRouter(
    prefix="/api/projects",
    tags=["project"],
    route_class=DishkaRoute,
    dependencies=[Depends(require_login)],
)


def _create_project(
    project_name: str,
    project_service: ProjectService,
    batch_service: BatchService,
    dataset_service: DatasetService,
    database_service: DatabaseService,
    metadata_import_service: MetadataImportService,
) -> Project:
    with database_service.get_session() as session:
        mapper_groups = list(database_service.get_default_mapper_groups(session))
        logging.info(
            f"Creating project {project_name} with mapper groups: {[group.name for group in mapper_groups]}"
        )
        dataset = metadata_import_service.create_dataset(project_name)
        dataset = dataset_service.create(
            dataset,
            [mapper.uid for group in mapper_groups for mapper in group.mappers],
            session=session,
        )
        project = metadata_import_service.create_project(project_name, dataset.uid)
        project.mapper_groups = [group.uid for group in mapper_groups]
        project = project_service.create(project, session=session)
        batch = Batch(
            uid=UUID(int=0),
            name="Default",
            status=BatchStatus.INITIALIZED,
            project_uid=project.uid,
            is_default=True,
            created=datetime.datetime.now(),
        )
        batch_service.create(batch, session=session)
        return project


def _export_project(
    project_uid: UUID,
    database_service: DatabaseService,
    metadata_export_service: MetadataExportService,
) -> Project:
    with database_service.get_session() as session:
        database_project = database_service.get_project(session, project_uid)
        if not database_project.completed:
            raise ValueError("Can only export a completed project.")
        for batch in database_project.batches:
            if not batch.completed:
                raise ValueError("Can only export completed batches.")
        if not database_project.valid:
            raise ValueError("Can only export a valid project.")
        logging.info("Exporting project to outbox")
        project = database_project.model
    metadata_export_service.export(project)
    return project


@project_router.post("/create")
async def create_project(
    project_service: FromDishka[ProjectService],
    batch_service: FromDishka[BatchService],
    dataset_service: FromDishka[DatasetService],
    database_service: FromDishka[DatabaseService],
    metadata_import_service: FromDishka[MetadataImportService],
) -> Project:
    """Create a project based on parameters in form.

    Returns
    ----------
    Project
        Response with created project's data.
    """
    project_name = "New project"
    try:
        project = _create_project(
            project_name,
            project_service,
            batch_service,
            dataset_service,
            database_service,
            metadata_import_service,
        )
        logging.debug(f"Created project {project.uid, project.name}")
        return project

    except Exception as exception:
        logging.error("Failed to parse create project due to error", exc_info=True)
        raise HTTPException(
            status_code=400, detail="Invalid project data"
        ) from exception


@project_router.get("")
async def get_projects(
    project_service: FromDishka[ProjectService],
) -> Iterable[Project]:
    """Get status of registered projects.

    Returns
    ----------
    Iterable[Project]
        List of registered projects
    """
    projects = project_service.get_all_of_root_schema()
    return projects


@project_router.post("/project/{project_uid}")
async def update_project(
    project_uid: UUID,
    project: Project,
    project_service: FromDishka[ProjectService],
) -> Project:
    """Update project specified by id with data from request body.

    Parameters
    ----------
    project_uid: UUID
        Id of project to update
    project: Project
        Project data to update

    Returns
    ----------
    Project
        Updated project data if successful.
    """
    try:
        updated_project = project_service.update(project)
        if updated_project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        logging.debug(f"Updated project {updated_project.uid, updated_project.name}")
        return updated_project
    except ValueError as exception:
        logging.error("Failed to parse file due to error", exc_info=True)
        raise HTTPException(
            status_code=400, detail="Invalid project data"
        ) from exception


@project_router.post("/project/{project_uid}/export")
async def export(
    project_uid: UUID,
    database_service: FromDishka[DatabaseService],
    metadata_export_service: FromDishka[MetadataExportService],
) -> Project:
    """Submit project specified by id to storage.

    Parameters
    ----------
    project_uid: UUID
        Id of project.

    Returns
    ----------
    Project
        Project data if successful.
    """
    project = _export_project(project_uid, database_service, metadata_export_service)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@project_router.get("/project/{project_uid}")
async def get_project(
    project_uid: UUID,
    project_service: FromDishka[ProjectService],
) -> Project:
    """Get status of project specified by id.

    Parameters
    ----------
    project_uid: UUID
        Id of project.

    Returns
    ----------
    Project
        Project data.
    """
    project = project_service.get_optional(project_uid)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@project_router.delete("/project/{project_uid}")
async def delete_project(
    project_uid: UUID,
    project_service: FromDishka[ProjectService],
):
    """Delete project specified by id.

    Parameters
    ----------
    project_uid: UUID
        Id of project.

    """
    deleted = project_service.delete(project_uid)
    if deleted is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if not deleted:
        raise HTTPException(status_code=400, detail="Project not deleted")


@project_router.get("/project/{project_uid}/validation")
async def get_project_validation(
    project_uid: UUID,
    validation_service: FromDishka[ValidationService],
) -> ProjectValidation:
    """Get validation of project specified by id.

    Parameters
    ----------
    project_uid: UUID
        Id of project to get validation of.

    Returns
    ----------
    ProjectValidation
        Validation data if successful.
    """
    validation = validation_service.get_validation_for_project(project_uid)
    logging.debug(f"Validation of project {project_uid}: {validation}")
    return validation
