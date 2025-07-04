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

"""FastAPI router for handling items."""
import logging
from http import HTTPStatus
from typing import Dict, List, Optional, Union
from uuid import UUID

from dishka.integrations.fastapi import (
    DishkaRoute,
    FromDishka,
)
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from slidetap.model import ImageStatus, TableRequest
from slidetap.model.item import AnyItem, ImageGroup, Item, item_factory
from slidetap.model.item_reference import ItemReference
from slidetap.model.item_select import ItemSelect
from slidetap.services import (
    DatabaseService,
    ItemService,
    SchemaService,
)
from slidetap.web.routers.login_router import require_login
from slidetap.web.services import (
    ImageExportService,
    ImageImportService,
    MetadataExportService,
)


class PreviewResponse(BaseModel):
    """Response model for item preview."""

    preview: str


class ItemsResponse(BaseModel):
    """Response model for items list with count."""

    items: List[AnyItem]
    count: int


item_router = APIRouter(
    prefix="/api/items",
    tags=["item"],
    route_class=DishkaRoute,
    dependencies=[Depends(require_login)],
)


@item_router.get("/item/{item_uid}")
async def get_item(
    item_uid: UUID,
    item_service: FromDishka[ItemService],
) -> AnyItem:
    """Get item by ID.

    Parameters
    ----------
    item_uid: UUID
        ID of the item

    Returns
    ----------
    AnyItem
        The requested item
    """
    logging.debug(f"Get item {item_uid}.")
    item = item_service.get(item_uid)
    if item is None:
        logging.error(f"Item {item_uid} not found.")
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Item {item_uid} not found",
        )
    return item


@item_router.get("/item/{item_uid}/preview")
async def preview_item(
    item_uid: UUID,
    metadata_export_service: FromDishka[MetadataExportService],
) -> PreviewResponse:
    """Return preview string for item.

    Parameters
    ----------
    item_uid: UUID
        ID of the item

    Returns
    ----------
    PreviewResponse
        Preview data for the item
    """
    logging.debug(f"Preview item {item_uid}.")
    preview = metadata_export_service.preview_item(item_uid)
    if preview is None:
        logging.error(f"Item {item_uid} not found.")
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Item {item_uid} not found",
        )
    return PreviewResponse(preview=preview)


@item_router.post("/item/{item_uid}/select")
async def select_item(
    item_uid: UUID, item_service: FromDishka[ItemService], value: ItemSelect
):
    """Select or de-select item.

    Parameters
    ----------
    item_uid: UUID
        ID of item to select
    value: bool
        Selection value (true to select, false to deselect)

    """
    logging.debug(f"Select item {item_uid}.")
    item = item_service.select(item_uid, value)
    if item is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Item {item_uid} not found",
        )


@item_router.post("/item/{item_uid}")
async def save_item(
    item_uid: UUID,
    item: AnyItem,
    item_service: FromDishka[ItemService],
) -> Item:
    """Update item with specified id.

    Parameters
    ----------
    item_uid: UUID
        ID of item to update
    item: AnyItem
        Item data to update

    Returns
    ----------
    Item
        Updated item
    """
    logging.debug(f"Save item {item_uid}.")
    updated_item = item_service.update(item)
    if updated_item is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Item {item_uid} not found",
        )
    return updated_item


@item_router.post("/add")
async def add_item(
    item_data: Dict,
    item_service: FromDishka[ItemService],
) -> AnyItem:
    """Add item to project.

    Parameters
    ----------
    item_data: Dict
        Item data

    Returns
    ----------
    AnyItem
        Created item
    """
    logging.debug("Add item.")
    item = item_factory(item_data)
    # TODO use project mappers
    created_item = item_service.add(item, [])
    return created_item


@item_router.post("/create")
async def create_item(
    item_service: FromDishka[ItemService],
    schema_uid: UUID = Query(..., alias="schemaUid"),
    project_uid: UUID = Query(..., alias="projectUid"),
    batch_uid: UUID = Query(..., alias="batchUid"),
) -> AnyItem:
    """Create item.

    Parameters
    ----------
    schema_uid: UUID
        Schema UID for the item
    project_uid: UUID
        Project UID
    batch_uid: UUID
        Batch UID

    Returns
    ----------
    AnyItem
        Created item
    """
    logging.debug("Create item.")
    item = item_service.create(schema_uid, project_uid, batch_uid)
    if item is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Failed to create item",
        )
    return item


@item_router.post("/item/{item_uid}/copy")
async def copy_item(
    item_uid: UUID,
    item_service: FromDishka[ItemService],
) -> AnyItem:
    """Copy item with specified id.

    Parameters
    ----------
    item_uid: UUID
        ID of item to copy

    Returns
    ----------
    AnyItem
        Copied item
    """
    logging.debug(f"Copy item {item_uid}.")
    copied_item = item_service.copy(item_uid)
    if copied_item is None:
        logging.error(f"Item {item_uid} not found.")
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Item {item_uid} not found",
        )
    return copied_item


@item_router.get("")
@item_router.post("")
async def get_items_get(
    item_service: FromDishka[ItemService],
    table_request: Optional[TableRequest] = None,
    dataset_uid: UUID = Query(..., alias="datasetUid"),
    item_schema_uid: UUID = Query(..., alias="itemSchemaUid"),
    batch_uid: Optional[UUID] = Query(None, alias="batchUid"),
) -> ItemsResponse:
    """Get items of specified type from dataset (GET method).

    Parameters
    ----------
    dataset_uid: UUID
        ID of dataset to get items from
    item_schema_uid: UUID
        Item schema to get
    batch_uid: Optional[UUID]
        Optional batch UID filter

    Returns
    ----------
    ItemsResponse
        Items and count
    """
    table_request = table_request or TableRequest()

    items = item_service.get_for_schema(
        item_schema_uid,
        dataset_uid,
        batch_uid,
        table_request.start,
        table_request.size,
        table_request.identifier_filter,
        table_request.attribute_filters,
        table_request.sorting,
        table_request.included,
        table_request.valid,
        table_request.status_filter,
        table_request.tag_filter,
    )
    count = item_service.get_count_for_schema(
        item_schema_uid,
        dataset_uid,
        batch_uid,
        table_request.identifier_filter,
        table_request.attribute_filters,
        table_request.included,
        table_request.valid,
        table_request.status_filter,
        table_request.tag_filter,
    )
    return ItemsResponse(items=list(items), count=count)


@item_router.get("/references")
async def get_references(
    item_service: FromDishka[ItemService],
    schema_service: FromDishka[SchemaService],
    dataset_uid: UUID = Query(..., alias="datasetUid"),
    item_schema_uid: UUID = Query(..., alias="itemSchemaUid"),
    batch_uid: Optional[UUID] = Query(None, alias="batchUid"),
) -> Dict[str, ItemReference]:
    """Get item references for schema.

    Parameters
    ----------
    dataset_uid: UUID
        Dataset UID
    item_schema_uid: UUID
        Item schema UID
    batch_uid: Optional[UUID]
        Optional batch UID filter

    Returns
    ----------
    Dict[str, ItemReference]
        Dictionary of item references keyed by UID
    """
    logging.debug(f"Get items of schema {item_schema_uid}.")
    item_schema = schema_service.get_item(item_schema_uid)
    if item_schema is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Item schema {item_schema_uid} not found",
        )
    items = item_service.get_references_for_schema(
        item_schema_uid, dataset_uid, batch_uid
    )
    return {str(item.uid): item for item in items}


@item_router.get("/item/{item_uid}/images")
async def get_images_for_item(
    item_uid: UUID,
    item_service: FromDishka[ItemService],
    group_by_schema_uid: UUID = Query(..., alias="groupBySchemaUid"),
    image_schema_uid: Optional[UUID] = Query(None, alias="imageSchemaUid"),
) -> List[ImageGroup]:
    """Get images for item.

    Parameters
    ----------
    item_uid: UUID
        ID of item to get images for
    group_by_schema_uid: UUID
        Schema UID to group by
    image_schema_uid: Optional[UUID]
        Optional image schema UID filter

    Returns
    ----------
    List[ImageGroup]
        List of image groups
    """
    logging.debug(f"Get images for item {item_uid} grouped by {group_by_schema_uid}.")
    groups = item_service.get_images_for_item(
        item_uid, group_by_schema_uid, image_schema_uid
    )
    return groups


@item_router.post("/retry")
async def retry(
    image_uids: List[UUID],
    database_service: FromDishka[DatabaseService],
    image_import_service: FromDishka[ImageImportService],
    image_export_service: FromDishka[ImageExportService],
):
    """Retry processing for failed images.

    Parameters
    ----------
    image_uids: List[UUID]
        List of image UIDs to retry
    """
    with database_service.get_session() as session:
        for image_uid in image_uids:
            image = database_service.get_image(session, image_uid)
            if image is None:
                raise ValueError(f"Image {image_uid} does not exist.")
            if image.batch is None:
                raise ValueError(f"Image {image_uid} does not belong to a batch.")
            image.status_message = ""
            if image.status == ImageStatus.DOWNLOADING_FAILED:
                image.reset_as_not_started()
                image_import_service.redo_image_download(image.model)
            elif image.status == ImageStatus.PRE_PROCESSING_FAILED:
                image.reset_as_downloaded()
                image_import_service.redo_image_pre_processing(image.model)
            elif image.status == ImageStatus.POST_PROCESSING_FAILED:
                image.reset_as_pre_processed()
                image_export_service.re_export(image.batch.model, image.model)
            session.commit()
