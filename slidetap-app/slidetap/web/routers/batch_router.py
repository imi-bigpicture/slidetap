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

"""FastAPI router for handling batches and items in batches."""
import logging
from typing import Iterable, Optional
from uuid import UUID

from dishka.integrations.fastapi import (
    DishkaRoute,
    FromDishka,
)
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from slidetap.model import Batch, BatchStatus
from slidetap.model.validation import BatchValidation
from slidetap.services import (
    BatchService,
    ValidationService,
)
from slidetap.web.services import (
    ImageExportService,
    ImageImportService,
    MetadataImportService,
)
from slidetap.web.services.login_service import require_login

batch_router = APIRouter(
    prefix="/api/batches",
    tags=["batch"],
    route_class=DishkaRoute,
    dependencies=[Depends(require_login)],
)


@batch_router.post("/create")
async def create_batch(
    batch: Batch,
    batch_service: FromDishka[BatchService],
) -> Batch:
    """Create a batch based on parameters in request body.

    Parameters
    ----------
    batch: Batch
        Batch data to create

    Returns
    ----------
    Batch
        Response with created batch's data.
    """
    try:
        created_batch = batch_service.create(batch)
        logging.debug(f"Created batch {created_batch.uid}")
        return created_batch
    except ValueError as exception:
        logging.error("Failed to create batch due to error", exc_info=True)
        raise HTTPException(
            status_code=400, detail="Failed to create batch"
        ) from exception


@batch_router.get("")
async def get_batches(
    batch_service: FromDishka[BatchService],
    project_uid: Optional[UUID] = Query(None),
    status: Optional[BatchStatus] = Query(None),
) -> Iterable[Batch]:
    """Get status of registered batches.

    Parameters
    ----------
    project_uid: Optional[UUID]
        Filter by project UID
    status: Optional[BatchStatus]
        Filter by batch status

    Returns
    ----------
    Iterable[Batch]
        List of registered batches
    """
    batches = batch_service.get_all(
        project_uid=project_uid,
        status=status,
    )
    return batches


@batch_router.post("/batch/{batch_uid}")
async def update_batch(
    batch_uid: UUID,
    batch: Batch,
    batch_service: FromDishka[BatchService],
) -> Batch:
    """Update batch specified by id with data from request body.

    Parameters
    ----------
    batch_uid: UUID
        Id of batch to update
    batch: Batch
        Batch data to update

    Returns
    ----------
    Batch
        Updated batch data if successful.
    """
    try:
        updated_batch = batch_service.update(batch)
        if updated_batch is None:
            raise HTTPException(status_code=404, detail="Batch not found")
        logging.debug(f"Updated batch {updated_batch.uid}, {updated_batch.name}")
        return updated_batch
    except ValueError as exception:
        logging.error("Failed to update batch due to error", exc_info=True)
        raise HTTPException(
            status_code=400, detail="Failed to update batch"
        ) from exception


@batch_router.post("/batch/{batch_uid}/uploadFile")
async def upload_batch_file(
    batch_uid: UUID,
    metadata_import_service: FromDishka[MetadataImportService],
    file: UploadFile = File(...),
) -> Batch:
    """Search for metadata and images for batch specified by id
    using search criteria specified in uploaded file.

    Parameters
    ----------
    batch_uid: UUID
        Id of batch to search.
    file: UploadFile
        File containing search criteria

    Returns
    ----------
    Batch
        Batch data if successful.
    """
    try:
        batch = metadata_import_service.search(
            batch_uid,
            file,
        )
        if batch is None:
            logging.error(f"No batch found with uid {batch_uid}.")
            raise HTTPException(status_code=404, detail="Batch not found")
        return batch
    except ValueError as exception:
        logging.error("Failed to parse file due to error", exc_info=True)
        raise HTTPException(
            status_code=400, detail="Failed to upload file"
        ) from exception


@batch_router.post("/batch/{batch_uid}/pre_process")
async def pre_process(
    batch_uid: UUID,
    image_import_service: FromDishka[ImageImportService],
) -> Batch:
    """Preprocess images for batch specified by id.

    Parameters
    ----------
    batch_uid: UUID
        Id of batch.

    Returns
    ----------
    Batch
        Batch data if successful.
    """
    logging.info(f"Pre-processing batch {batch_uid}.")
    batch = image_import_service.pre_process_batch(batch_uid)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")
    return batch


@batch_router.post("/batch/{batch_uid}/process")
async def process(
    batch_uid: UUID,
    image_export_service: FromDishka[ImageExportService],
) -> Batch:
    """Start batch specified by id. Accepts selected items in
     batch and start downloading images.

    Parameters
    ----------
    batch_uid: UUID
        Id of batch.

    Returns
    ----------
    Batch
        Batch data if successful.
    """
    logging.info(f"Processing batch {batch_uid}.")
    batch = image_export_service.export(batch_uid)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")
    return batch


@batch_router.post("/batch/{batch_uid}/complete")
async def complete(
    batch_uid: UUID,
    batch_service: FromDishka[BatchService],
) -> Batch:
    """Complete batch specified by id.

    Parameters
    ----------
    batch_uid: UUID
        Id of batch.

    Returns
    ----------
    Batch
        Batch data if successful.
    """
    logging.info(f"Completing batch {batch_uid}.")
    batch = batch_service.set_as_completed(batch_uid)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")
    return batch


@batch_router.get("/batch/{batch_uid}")
async def get_batch(
    batch_uid: UUID,
    batch_service: FromDishka[BatchService],
) -> Batch:
    """Get status of batch specified by id.

    Parameters
    ----------
    batch_uid: UUID
        Id of batch.

    Returns
    ----------
    Batch
        Batch data.
    """
    batch = batch_service.get(batch_uid)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")
    return batch


@batch_router.delete("/batch/{batch_uid}")
async def delete_batch(
    batch_uid: UUID,
    batch_service: FromDishka[BatchService],
):
    """Delete batch specified by id.

    Parameters
    ----------
    batch_uid: UUID
        Id of batch.

    Returns
    ----------
    dict
        Ok status if successful.
    """
    batch = batch_service.delete(batch_uid)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")
    if batch.status != BatchStatus.DELETED:
        raise HTTPException(status_code=400, detail="Batch could not be deleted")
    return {"status": "ok"}


@batch_router.get("/batch/{batch_uid}/validation")
async def get_validation(
    batch_uid: UUID,
    validation_service: FromDishka[ValidationService],
) -> BatchValidation:
    """Get validation of batch specified by id.

    Parameters
    ----------
    batch_uid: UUID
        Id of batch to get validation of.

    Returns
    ----------
    BatchValidation
        Validation data if successful.
    """
    validation = validation_service.get_validation_for_batch(batch_uid)
    logging.debug(f"Validation of batch {batch_uid}: {validation}")
    return validation
