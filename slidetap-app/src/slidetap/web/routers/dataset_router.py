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

"""FastAPI router for handling datasets."""
from http import HTTPStatus
from typing import List
from uuid import UUID

from dishka.integrations.fastapi import (
    DishkaRoute,
    FromDishka,
)
from fastapi import APIRouter, Depends, HTTPException

from slidetap.model import Dataset
from slidetap.services import DatasetService
from slidetap.web.services.login_service import require_valid_token_and_refresh

dataset_router = APIRouter(
    prefix="/api/datasets",
    tags=["dataset"],
    route_class=DishkaRoute,
    dependencies=[Depends(require_valid_token_and_refresh)],
)


@dataset_router.get("/importable")
async def importable_datasets() -> List[Dataset]:
    """Get importable datasets.

    Returns
    ----------
    List[Dataset]
        List of importable datasets
    """
    # This functionality is not implemented in the original controller
    # Keeping as placeholder that raises not implemented error
    raise HTTPException(
        status_code=HTTPStatus.NOT_IMPLEMENTED,
        detail="Importable datasets functionality not implemented",
    )


@dataset_router.post("/import")
async def import_dataset(dataset: Dataset) -> Dataset:
    """Import a dataset.

    Parameters
    ----------
    dataset: Dataset
        Dataset to import

    Returns
    ----------
    Dataset
        Imported dataset
    """
    # This functionality is not implemented in the original controller
    # Keeping as placeholder that raises not implemented error
    raise HTTPException(
        status_code=HTTPStatus.NOT_IMPLEMENTED,
        detail="Dataset import functionality not implemented",
    )


@dataset_router.get("")
async def get_datasets() -> List[Dataset]:
    """Get all datasets.

    Returns
    ----------
    List[Dataset]
        List of all datasets
    """
    # This functionality is not implemented in the original controller
    # Keeping as placeholder that raises not implemented error
    raise HTTPException(
        status_code=HTTPStatus.NOT_IMPLEMENTED,
        detail="Get datasets functionality not implemented",
    )


@dataset_router.delete("/dataset/{dataset_uid}")
async def delete_dataset(dataset_uid: UUID) -> dict:
    """Delete dataset specified by id.

    Parameters
    ----------
    dataset_uid: UUID
        Id of dataset to delete.

    Returns
    ----------
    dict
        Success message if successful.
    """
    # This functionality is not implemented in the original controller
    # Keeping as placeholder that raises not implemented error
    raise HTTPException(
        status_code=HTTPStatus.NOT_IMPLEMENTED,
        detail="Dataset deletion functionality not implemented",
    )


@dataset_router.get("/dataset/{dataset_uid}")
async def get_dataset(
    dataset_uid: UUID,
    dataset_service: FromDishka[DatasetService],
) -> Dataset:
    """Get dataset specified by id.

    Parameters
    ----------
    dataset_uid: UUID
        Id of dataset.

    Returns
    ----------
    Dataset
        Dataset data.
    """
    dataset = dataset_service.get(dataset_uid)
    if dataset is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Dataset with id {dataset_uid} not found",
        )
    return dataset


@dataset_router.post("/dataset/{dataset_uid}")
async def update_dataset(
    dataset_uid: UUID,
    dataset: Dataset,
    dataset_service: FromDishka[DatasetService],
) -> Dataset:
    """Update dataset specified by id.

    Parameters
    ----------
    dataset_uid: UUID
        Id of dataset to update.
    dataset: Dataset
        Updated dataset data.

    Returns
    ----------
    Dataset
        Updated dataset.
    """
    updated_dataset = dataset_service.update(dataset)
    if updated_dataset is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Dataset with id {dataset_uid} not found",
        )
    return updated_dataset