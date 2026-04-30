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

"""FastAPI router for per-unit metadata search items."""

from http import HTTPStatus
from typing import List
from uuid import UUID

from dishka.integrations.fastapi import (
    DishkaRoute,
    FromDishka,
)
from fastapi import APIRouter, Depends, HTTPException, Query

from slidetap.model import MetadataSearchItem
from slidetap.web.routers.login_router import require_valid_token
from slidetap.web.services import MetadataImportService


metadata_search_router = APIRouter(
    prefix="/api/metadata-search",
    tags=["metadata-search"],
    route_class=DishkaRoute,
    dependencies=[Depends(require_valid_token)],
)


@metadata_search_router.get("/supports-retry")
async def supports_retry(
    metadata_import_service: FromDishka[MetadataImportService],
) -> bool:
    """Whether the active importer supports per-search-item retry."""
    return metadata_import_service.supports_retry


@metadata_search_router.get("/items")
async def list_search_items(
    metadata_import_service: FromDishka[MetadataImportService],
    batch_uid: UUID = Query(..., alias="batchUid"),
) -> List[MetadataSearchItem]:
    """List search items for a batch.

    Parameters
    ----------
    batch_uid: UUID
        The batch to list search items for.

    Returns
    -------
    List[MetadataSearchItem]
        All search items in the batch, including in-flight, complete and
        failed.
    """
    return metadata_import_service.list_search_items(batch_uid)


@metadata_search_router.post("/items/{search_item_uid}/retry")
async def retry_search_item(
    search_item_uid: UUID,
    metadata_import_service: FromDishka[MetadataImportService],
):
    """Retry a previously-failed search item.

    Parameters
    ----------
    search_item_uid: UUID
        UID of the FAILED search item to retry.
    """
    try:
        metadata_import_service.retry_search_item(search_item_uid)
    except ValueError as e:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@metadata_search_router.post("/items/{search_item_uid}/exclude")
async def exclude_search_item(
    search_item_uid: UUID,
    metadata_import_service: FromDishka[MetadataImportService],
):
    """Delete a FAILED search item to remove it from the user's view."""
    metadata_import_service.exclude_search_item(search_item_uid)
