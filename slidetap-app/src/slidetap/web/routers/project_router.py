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

import logging
from collections.abc import Iterable
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from dishka.integrations.fastapi import (
    DishkaRoute,
    FromDishka,
)
from fastapi import APIRouter, Depends, HTTPException

from slidetap.model import (
    MigrationAttributeIssue,
    MigrationDecision,
    NotAllowedActionError,
    Project,
    ProjectActions,
    ProjectMigration,
    ProjectNotEditableError,
)
from slidetap.model.private_attribute_summary import PrivateAttributeSummary
from slidetap.model.validation import ProjectValidation
from slidetap.services import (
    ItemService,
    MigrationService,
    ProjectService,
    ValidationService,
)
from slidetap.task import Scheduler
from slidetap.web.routers.dependencies import create_logger_dependency
from slidetap.web.routers.responses import RepseudonymizeResponse, StatusResponse
from slidetap.web.services import (
    ImagePipelineService,
    MetadataExportService,
    MetadataImportService,
)
from slidetap.web.services.login_service import require_valid_token

Logger = Annotated[logging.Logger, Depends(create_logger_dependency(__name__))]

project_router = APIRouter(
    prefix="/api/projects",
    tags=["project"],
    route_class=DishkaRoute,
    dependencies=[Depends(require_valid_token)],
)


@project_router.post("/create")
async def create_project(
    metadata_import_service: FromDishka[MetadataImportService],
    logger: Logger,
) -> Project:
    """Create a project based on parameters in form.

    Returns
    ----------
    Project
        Response with created project's data.
    """
    try:
        return metadata_import_service.create_project("New project")

    except ValueError as exception:
        logger.error("Failed to parse create project due to error", exc_info=True)
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Invalid project data"
        ) from exception


@project_router.get("")
async def get_projects(
    project_service: FromDishka[ProjectService],
) -> Iterable[Project]:
    """Get status of registered projects.

    The projects of every root schema.

    Returns
    ----------
    Iterable[Project]
        List of registered projects
    """
    projects = project_service.get_all()
    return projects


@project_router.post("/project/{project_uid}")
async def update_project(
    project_uid: UUID,
    project: Project,
    project_service: FromDishka[ProjectService],
    logger: Logger,
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
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND, detail="Project not found"
            )
        logger.debug(f"Updated project {updated_project.uid, updated_project.name}")
        return updated_project
    except ValueError as exception:
        logger.error("Failed to parse file due to error", exc_info=True)
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Invalid project data"
        ) from exception


@project_router.post("/project/{project_uid}/complete")
async def complete(
    project_uid: UUID,
    project_service: FromDishka[ProjectService],
    image_pipeline_service: FromDishka[ImagePipelineService],
    logger: Logger,
) -> Project:
    """Write the images of every curated batch of the project to the outbox.

    The last point at which a batch can be taken back into curation: until this
    is done the images are the application's, and afterwards they are in the
    bundle that is handed over.

    Parameters
    ----------
    project_uid: UUID
        Id of project.

    Returns
    ----------
    Project
        Project data.
    """
    project = project_service.get_completed(project_uid)
    if project is None:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Can only complete a project whose batches are all curated.",
        )
    logger.info(f"Storing images of project {project_uid} to outbox.")
    try:
        await image_pipeline_service.store_project(project_uid)
    except NotAllowedActionError as exception:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT, detail=str(exception)
        ) from exception
    return project


@project_router.post("/project/{project_uid}/export")
async def export(
    project_uid: UUID,
    project_service: FromDishka[ProjectService],
    item_service: FromDishka[ItemService],
    metadata_export_service: FromDishka[MetadataExportService],
    logger: Logger,
) -> Project:
    """Submit project specified by id to storage.

    Refused, with the reason, for a project that is not wholly in the outbox:
    one that is not completed, one with a batch that is not completed or is
    being deleted, or one with a selected image that was never stored.

    Parameters
    ----------
    project_uid: UUID
        Id of project.

    Returns
    ----------
    Project
        Project data if successful.
    """
    try:
        project = project_service.get_exportable(project_uid)
    except NotAllowedActionError as exception:
        logger.info(f"Refused export of project {project_uid}: {exception}")
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT, detail=str(exception)
        ) from exception
    logger.info("Exporting project to outbox")
    # An item is named in a bundle by its pseudonym and by nothing else, and
    # what writes the bundle leaves out what it has not been given: without
    # this the export writes elements nothing can name or point at, and says
    # nothing about having done so.
    missing = item_service.items_missing_pseudonym(project.dataset_uid)
    if missing > 0:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=(
                f"{missing} items to export have no pseudonym. A project whose "
                f"pseudonyms have been cleared cannot be exported."
            ),
        )
    try:
        await metadata_export_service.export(project)
    except NotAllowedActionError as exception:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT, detail=str(exception)
        ) from exception
    return project


@project_router.post("/project/{project_uid}/repseudonymize")
async def repseudonymize(
    project_uid: UUID,
    project_service: FromDishka[ProjectService],
    item_service: FromDishka[ItemService],
    logger: Logger,
) -> RepseudonymizeResponse:
    """Give every item of the project's dataset a new pseudonym.

    For a dataset that has to go out again unlinkable to what went out before.
    The pseudonyms are the dataset's own, minted when its items were created
    and read by everything that writes it out, so a new set is given here and
    written out by exporting the project again.

    Only for a completed, exported or failed project. An export that follows
    is what puts the new pseudonyms in a bundle.

    Parameters
    ----------
    project_uid: UUID
        Id of project.

    Returns
    ----------
    RepseudonymizeResponse
        How many items were given a new pseudonym.
    """
    try:
        project = project_service.get_settled(project_uid)
    except NotAllowedActionError as exception:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail=str(exception)
        ) from exception
    try:
        changed = item_service.repseudonymize(project.dataset_uid)
    except NotAllowedActionError as exception:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT, detail=str(exception)
        ) from exception
    except ValueError as exception:
        logger.error("Failed to repseudonymize project.", exc_info=True)
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail=str(exception)
        ) from exception
    logger.info(f"Gave {changed} items of project {project_uid} new pseudonyms.")
    return RepseudonymizeResponse(changed=changed)


@project_router.post("/project/{project_uid}/clear_pseudonyms")
async def clear_pseudonyms(
    project_uid: UUID,
    project_service: FromDishka[ProjectService],
    item_service: FromDishka[ItemService],
    logger: Logger,
) -> RepseudonymizeResponse:
    """Take the pseudonyms off the project's dataset.

    For a dataset that is to stop carrying the link to what was handed over:
    the pseudonym is what ties an item to the element that went out under it.
    Afterwards the project cannot be exported, which is what the export refuses
    on, and there is nothing that puts the pseudonyms back.

    Only for a completed, exported or failed project, as giving it new ones is.

    Parameters
    ----------
    project_uid: UUID
        Id of project.

    Returns
    ----------
    RepseudonymizeResponse
        How many items had their pseudonym taken off.
    """
    try:
        project = project_service.get_settled(project_uid)
    except NotAllowedActionError as exception:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail=str(exception)
        ) from exception
    cleared = item_service.clear_pseudonyms(project.dataset_uid)
    logger.info(f"Took the pseudonym off {cleared} items of project {project_uid}.")
    return RepseudonymizeResponse(changed=cleared)


@project_router.post("/project/{project_uid}/pseudonymize_identifiers")
async def pseudonymize_identifiers(
    project_uid: UUID,
    project_service: FromDishka[ProjectService],
    item_service: FromDishka[ItemService],
    logger: Logger,
) -> RepseudonymizeResponse:
    """Overwrite the identifier of every item that has a pseudonym with it.

    The opposite of ``clear_pseudonyms``: the link is cut on the side of the
    identifiers instead. Only for a completed, exported or failed project, as
    the other two pseudonym operations are.

    Parameters
    ----------
    project_uid: UUID
        Id of project.

    Returns
    ----------
    RepseudonymizeResponse
        How many identifiers were replaced with the item's pseudonym.
    """
    try:
        project = project_service.get_settled(project_uid)
    except NotAllowedActionError as exception:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail=str(exception)
        ) from exception
    try:
        replaced = item_service.pseudonymize_identifiers(project.dataset_uid)
    except ProjectNotEditableError:
        # Refused with 409, as on every endpoint.
        raise
    except NotAllowedActionError as exception:
        logger.error("Failed to pseudonymize project identifiers.", exc_info=True)
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail=str(exception)
        ) from exception
    logger.info(
        f"Replaced the identifier of {replaced} items of project {project_uid} "
        f"with their pseudonym."
    )
    return RepseudonymizeResponse(changed=replaced)


@project_router.get("/project/{project_uid}/private_attributes")
async def get_private_attributes(
    project_uid: UUID,
    project_service: FromDishka[ProjectService],
    item_service: FromDishka[ItemService],
) -> PrivateAttributeSummary:
    """What private attributes the project's dataset and its items hold.

    Counted by item schema and attribute schema, without any values: what
    removing them would delete.

    Parameters
    ----------
    project_uid: UUID
        Id of project.

    Returns
    ----------
    PrivateAttributeSummary
        The private attributes by owner and attribute schema.
    """
    project = project_service.get(project_uid)
    return item_service.private_attribute_summary(project.dataset_uid)


@project_router.post("/project/{project_uid}/remove_private_attributes")
async def remove_private_attributes(
    project_uid: UUID,
    project_service: FromDishka[ProjectService],
    item_service: FromDishka[ItemService],
    logger: Logger,
) -> PrivateAttributeSummary:
    """Delete every private attribute of the project's dataset and its items.

    Only for a completed, exported or failed project: nothing that is still
    being curated loses what it was imported with.

    Parameters
    ----------
    project_uid: UUID
        Id of project.

    Returns
    ----------
    PrivateAttributeSummary
        What was removed, by owner and attribute schema.
    """
    try:
        project = project_service.get_settled(project_uid)
    except NotAllowedActionError as exception:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail=str(exception)
        ) from exception
    removed = item_service.remove_private_attributes(project.dataset_uid)
    logger.info(
        f"Removed the private attributes of {len(removed.attributes)} schemas from "
        f"the dataset of project {project_uid}."
    )
    return removed


@project_router.post("/project/{project_uid}/clear_seed")
async def clear_seed(
    project_uid: UUID,
    project_service: FromDishka[ProjectService],
    logger: Logger,
) -> Project:
    """Take the importer seed off the project.

    Only for a completed, exported or failed project: like clearing the
    pseudonyms, it cuts a link back to where the items came from. There is no way back:
    nothing remints a cleared seed, and any future import into this project's
    dataset falls back to whatever the importer does without one.

    Parameters
    ----------
    project_uid: UUID
        Id of project.

    Returns
    ----------
    Project
        The project, seed cleared.
    """
    try:
        project_service.get_settled(project_uid)
    except NotAllowedActionError as exception:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail=str(exception)
        ) from exception
    project = project_service.clear_seed(project_uid)
    logger.info(f"Cleared the importer seed of project {project_uid}.")
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
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Project not found"
        )
    return project


@project_router.get("/project/{project_uid}/actions")
async def get_project_actions(
    project_uid: UUID,
    project_service: FromDishka[ProjectService],
) -> ProjectActions:
    """Get what can be done with the project specified by id.

    What the application can do with the projects on its root schema, with
    the project's state applied, and whether a schema migration can migrate
    it.

    Parameters
    ----------
    project_uid: UUID
        Id of project.

    Returns
    ----------
    ProjectActions
        Which of the actions the project can be offered.
    """
    return project_service.get_actions(project_uid)


@project_router.get("/project/{project_uid}/migration")
async def get_project_migration(
    project_uid: UUID,
    migration_service: FromDishka[MigrationService],
) -> ProjectMigration:
    """Get the migration of the project to another root schema, with its
    state and its plan: the attribute issues to decide and the attributes
    dropped, by object. Not found where the project has no migration.

    Parameters
    ----------
    project_uid: UUID
        Id of project.

    Returns
    ----------
    ProjectMigration
        The migration.
    """
    return migration_service.get(project_uid)


@project_router.post("/project/{project_uid}/migration")
async def create_project_migration(
    project_uid: UUID,
    migration_service: FromDishka[MigrationService],
    scheduler: FromDishka[Scheduler],
    logger: Logger,
) -> ProjectMigration:
    """Create the migration of the project to another root schema.

    The project is migrating, and nothing can be changed of it, until the
    migration is completed or reverted. The migration is planned in a task.

    Parameters
    ----------
    project_uid: UUID
        Id of project.

    Returns
    ----------
    ProjectMigration
        The migration, being planned.
    """
    try:
        migration = migration_service.create(project_uid)
    except NotAllowedActionError as exception:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT, detail=str(exception)
        ) from exception
    try:
        await scheduler.plan_migration(project_uid)
    except Exception as exception:
        # Set as migrating already, and nothing would ever plan it.
        logger.error(f"Failed to start migrating project {project_uid}", exc_info=True)
        migration_service.revert(project_uid)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Failed to start the migration",
        ) from exception
    return migration


@project_router.put(
    "/project/{project_uid}/migration/attribute-issues/{attribute_issue_uid}"
)
async def decide_project_migration_attribute_issue(
    project_uid: UUID,
    attribute_issue_uid: UUID,
    decision: MigrationDecision,
    migration_service: FromDishka[MigrationService],
) -> MigrationAttributeIssue:
    """Decide an attribute issue of the migration of the project: a value on
    its attribute schema, or left empty.

    Parameters
    ----------
    project_uid: UUID
        Id of project.
    attribute_issue_uid: UUID
        Id of the attribute issue.
    decision: MigrationDecision
        The value, or none to leave the attribute empty.

    Returns
    ----------
    MigrationAttributeIssue
        The attribute issue, decided.
    """
    try:
        return migration_service.decide(project_uid, attribute_issue_uid, decision)
    except NotAllowedActionError as exception:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT, detail=str(exception)
        ) from exception


@project_router.post("/project/{project_uid}/migration/submit")
async def submit_project_migration(
    project_uid: UUID,
    migration_service: FromDishka[MigrationService],
    scheduler: FromDishka[Scheduler],
    logger: Logger,
) -> ProjectMigration:
    """Complete the migration of the project, with every attribute issue
    decided, in a task.

    Parameters
    ----------
    project_uid: UUID
        Id of project.

    Returns
    ----------
    ProjectMigration
        The migration, being completed.
    """
    try:
        migration = migration_service.submit(project_uid)
    except NotAllowedActionError as exception:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT, detail=str(exception)
        ) from exception
    try:
        await scheduler.complete_migration(project_uid)
    except Exception as exception:
        logger.error(
            f"Failed to start completing the migration of project {project_uid}",
            exc_info=True,
        )
        migration_service.resume_curating(project_uid)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Failed to start completing the migration",
        ) from exception
    return migration


@project_router.delete("/project/{project_uid}/migration")
async def revert_project_migration(
    project_uid: UUID,
    migration_service: FromDishka[MigrationService],
) -> Project:
    """Revert the migration of the project: remove it and its plan, and set
    the project back to the status it had.

    Also for a migration that failed, or whose task was lost. Nothing of the
    project is changed until a migration is completed.

    Parameters
    ----------
    project_uid: UUID
        Id of project.

    Returns
    ----------
    Project
        The project, with the status it had.
    """
    return migration_service.revert(project_uid)


@project_router.delete("/project/{project_uid}")
async def delete_project(
    project_uid: UUID,
    project_service: FromDishka[ProjectService],
    scheduler: FromDishka[Scheduler],
    logger: Logger,
) -> StatusResponse:
    """Schedule the deletion of the project specified by id.

    The project is marked as deleting and the work runs in a background
    task; the response returns immediately. Refused while the project is
    being exported or a worker holds one of its batches.

    Parameters
    ----------
    project_uid: UUID
        Id of project.

    Returns
    ----------
    StatusResponse
        Scheduled status if successful.
    """
    project = project_service.get_optional(project_uid)
    if project is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Project not found"
        )
    try:
        project = project_service.set_as_deleting(project_uid)
    except NotAllowedActionError as exception:
        logger.info(f"Refused deletion of project {project_uid}: {exception}.")
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT, detail=str(exception)
        ) from exception
    logger.info(f"Scheduling deletion of project {project_uid}.")
    await scheduler.delete_project(project)
    return StatusResponse(status="scheduled")


@project_router.get("/project/{project_uid}/validation")
async def get_project_validation(
    project_uid: UUID,
    validation_service: FromDishka[ValidationService],
    logger: Logger,
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
    logger.debug(f"Validation of project {project_uid}: {validation}")
    return validation
