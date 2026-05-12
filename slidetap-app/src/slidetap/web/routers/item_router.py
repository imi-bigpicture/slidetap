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
from typing import Annotated, Dict, List, Optional, Sequence, Iterable
from uuid import UUID

from dishka.integrations.fastapi import (
    DishkaRoute,
    FromDishka,
)
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from slidetap.model import (
    AnyItem,
    ImageGroup,
    MoveAttributeRequest,
    MoveAttributeResponse,
    TableRequest,
)
from slidetap.model.item_reference import ItemReference
from slidetap.model.item_select import ItemSelect
from slidetap.model.overview import OverviewRoot
from slidetap.services import (
    ItemService,
    MapperService,
    OverviewService,
    SchemaService,
)
from slidetap.web.routers.dependencies import create_logger_dependency
from slidetap.web.routers.login_router import require_valid_token
from slidetap.web.services import (
    ImagePipelineService,
    MetadataExportService,
)

Logger = Annotated[logging.Logger, Depends(create_logger_dependency(__name__))]


class PreviewResponse(BaseModel):
    """Response model for item preview."""

    preview: str


class ItemsResponse(BaseModel):
    """Response model for items list with count."""

    items: List[AnyItem]
    count: int


class ItemReferencesResponse(BaseModel):
    """Response model for item references keyed by UID."""

    references: Dict[str, ItemReference]


item_router = APIRouter(
    prefix="/api/items",
    tags=["item"],
    route_class=DishkaRoute,
    dependencies=[Depends(require_valid_token)],
)


@item_router.get("/item/{item_uid}")
async def get_item(
    item_uid: UUID,
    item_service: FromDishka[ItemService],
    logger: Logger,
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
    logger.debug(f"Get item {item_uid}.")
    item = item_service.get_optional(item_uid)
    if item is None:
        logger.error(f"Item {item_uid} not found.")
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Item {item_uid} not found",
        )
    return item


@item_router.get("/item/{item_uid}/preview")
async def preview_item(
    item_uid: UUID,
    metadata_export_service: FromDishka[MetadataExportService],
    logger: Logger,
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
    logger.debug(f"Preview item {item_uid}.")
    preview = metadata_export_service.preview_item(item_uid)
    if preview is None:
        logger.error(f"Item {item_uid} not found.")
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Item {item_uid} not found",
        )
    return PreviewResponse(preview=preview)


@item_router.post("/item/{item_uid}/select")
async def select_item(
    item_uid: UUID,
    item_service: FromDishka[ItemService],
    value: ItemSelect,
    logger: Logger,
) -> None:
    """Select or de-select item.

    Parameters
    ----------
    item_uid: UUID
        ID of item to select
    value: bool
        Selection value (true to select, false to deselect)

    """
    logger.debug(f"Select item {item_uid}.")
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
    logger: Logger,
) -> AnyItem:
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
    logger.debug(f"Save item {item_uid}.")
    updated_item = item_service.update(item)
    if updated_item is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Item {item_uid} not found",
        )
    return updated_item


@item_router.post("/add")
async def add_item(
    item: AnyItem,
    item_service: FromDishka[ItemService],
    logger: Logger,
) -> AnyItem:
    """Add item to project. FastAPI validates ``item`` against the
    discriminated ``AnyItem`` union — invalid payloads surface as 422.
    """
    logger.debug("Add item.")
    return item_service.add(item)


@item_router.post("/create")
async def create_item(
    item_service: FromDishka[ItemService],
    logger: Logger,
    schema_uid: UUID = Query(..., alias="schemaUid"),
    batch_uid: UUID = Query(..., alias="batchUid"),
    target_parent_uids: Optional[Sequence[UUID]] = Query(
        None, alias="targetParentUids"
    ),
    identifier: Optional[str] = Query(None),
) -> AnyItem:
    """Create an item in the given batch.

    Parameters
    ----------
    schema_uid: UUID
        Schema UID for the new item.
    batch_uid: UUID
        Batch the new item belongs to. Dataset and project are derived.
    target_parent_uids: Optional[Sequence[UUID]]
        Existing items to attach the new item to as a child.
    identifier: Optional[str]
        Identifier to assign. Falls back to the configured
        ``ItemNamingFactoryInterface`` when not provided.
    """
    logger.debug("Create item.")
    item = item_service.create(
        schema_uid,
        batch_uid,
        target_parent_uids=target_parent_uids,
        identifier=identifier,
    )
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
    logger: Logger,
    target_parent_uids: Optional[Sequence[UUID]] = Query(
        None, alias="targetParentUids"
    ),
    identifier: Optional[str] = Query(None),
) -> AnyItem:
    """Copy an item.

    Parameters
    ----------
    item_uid: UUID
        ID of item to copy.
    target_parent_uids: Optional[Sequence[UUID]]
        Existing items to attach the copy to as a child.
    identifier: Optional[str]
        Identifier for the copy. Falls back to ``<original> (copy)`` when
        not provided.
    """
    logger.debug(f"Copy item {item_uid} target_parents={target_parent_uids}.")
    copied_item = item_service.copy(
        item_uid,
        target_parent_uids=target_parent_uids,
        identifier=identifier,
    )
    if copied_item is None:
        logger.error(f"Item {item_uid} not found.")
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
        table_request.pseudonym_mode,
        table_request.attribute_filters,
        table_request.relation_filters,
        table_request.tag_filter,
        table_request.sorting,
        table_request.included,
        table_request.valid,
        table_request.status_filter,
    )
    count = item_service.get_count_for_schema(
        item_schema_uid,
        dataset_uid,
        batch_uid,
        table_request.identifier_filter,
        table_request.pseudonym_mode,
        table_request.attribute_filters,
        table_request.relation_filters,
        table_request.tag_filter,
        table_request.included,
        table_request.valid,
        table_request.status_filter,
    )
    return ItemsResponse(items=list(items), count=count)


@item_router.get("/references")
async def get_references(
    item_service: FromDishka[ItemService],
    schema_service: FromDishka[SchemaService],
    logger: Logger,
    dataset_uid: UUID = Query(..., alias="datasetUid"),
    item_schema_uid: UUID = Query(..., alias="itemSchemaUid"),
    batch_uid: Optional[UUID] = Query(None, alias="batchUid"),
) -> ItemReferencesResponse:
    """Get item references for schema, keyed by UID."""
    logger.debug(f"Get items of schema {item_schema_uid}.")
    item_schema = schema_service.get_item(item_schema_uid)
    if item_schema is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Item schema {item_schema_uid} not found",
        )
    items = item_service.get_references_for_schema(
        item_schema_uid, dataset_uid, batch_uid
    )
    return ItemReferencesResponse(
        references={str(item.uid): item for item in items}
    )


@item_router.get("/item/{item_uid}/images")
async def get_images_for_item(
    item_uid: UUID,
    item_service: FromDishka[ItemService],
    logger: Logger,
    group_by_schema_uid: UUID = Query(..., alias="groupBySchemaUid"),
    image_schema_uid: Optional[UUID] = Query(None, alias="imageSchemaUid"),
) -> Iterable[ImageGroup]:
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
    logger.debug(f"Get images for item {item_uid} grouped by {group_by_schema_uid}.")
    groups = item_service.get_images_for_item(
        item_uid, group_by_schema_uid, image_schema_uid
    )
    return groups


@item_router.get("/item/{item_uid}/overview/{overview_layout_uid}")
async def get_overview_data(
    item_uid: UUID,
    overview_layout_uid: UUID,
    overview_service: FromDishka[OverviewService],
    schema_service: FromDishka[SchemaService],
    logger: Logger,
    pseudonym_mode: bool = Query(False, alias="pseudonymMode"),
) -> OverviewRoot:
    """Get overview data for an item using the specified overview layout.

    Parameters
    ----------
    item_uid: UUID
        ID of the parent item
    overview_layout_uid: UUID
        UID of the overview layout to use

    Returns
    ----------
    OverviewRoot
        Overview data with groups and context attributes
    """
    logger.debug(f"Get overview for item {item_uid} with layout {overview_layout_uid}.")
    root_schema = schema_service.get_root()
    overview_layout = next(
        (
            layout
            for layout in root_schema.overview_layouts
            if layout.uid == overview_layout_uid
        ),
        None,
    )
    if overview_layout is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Overview layout {overview_layout_uid} not found",
        )
    try:
        data = overview_service.get_overview_data(
            item_uid, overview_layout, pseudonym_mode
        )
    except ValueError as exception:
        logger.error(
            f"Invalid overview request for item {item_uid}", exc_info=True
        )
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Invalid overview request",
        ) from exception
    if data is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Item {item_uid} not found",
        )
    return data


@item_router.post("/move-attribute")
async def move_attribute(
    request: MoveAttributeRequest,
    item_service: FromDishka[ItemService],
    logger: Logger,
) -> MoveAttributeResponse:
    """Swap a single attribute value between two items. Either swap with an
    existing item (``target_item_uid``) or create a new child of a parent
    with the source's schema and swap with it (``target_parent_uid``).
    """
    logger.debug(
        f"Moving attribute '{request.attribute_tag}' from item "
        f"{request.source_item_uid} (target_item={request.target_item_uid}, "
        f"target_parent={request.target_parent_uid})"
    )
    try:
        created_uid = item_service.move_attribute(
            request.source_item_uid,
            request.attribute_tag,
            target_item_uid=request.target_item_uid,
            target_parent_uid=request.target_parent_uid,
        )
    except ValueError as exception:
        logger.error(
            f"Invalid move-attribute request from item "
            f"{request.source_item_uid}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Invalid move-attribute request",
        ) from exception
    return MoveAttributeResponse(created_item_uid=created_uid)


@item_router.post("/retry")
async def retry(
    image_uids: List[UUID],
    image_pipeline_service: FromDishka[ImagePipelineService],
    logger: Logger,
) -> None:
    """Retry processing for failed or stuck images.

    Parameters
    ----------
    image_uids: List[UUID]
        List of image UIDs to retry
    """
    logger.debug(f"Retry images {image_uids}.")
    for image_uid in image_uids:
        image_pipeline_service.retry(image_uid)


@item_router.post("/item/{item_uid}/remap")
async def remap_item_attributes(
    item_uid: UUID,
    item_service: FromDishka[ItemService],
    mapper_service: FromDishka[MapperService],
    logger: Logger,
) -> None:
    """Re-apply the project's mappers to one item's attributes."""
    logger.info(f"Remap item {item_uid}.")
    if item_service.get_optional(item_uid) is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail=f"Item {item_uid} not found"
        )
    mapper_service.remap_item(item_uid)


@item_router.post("/item/{item_uid}/remap_hierarchy")
async def remap_item_hierarchy_attributes(
    item_uid: UUID,
    item_service: FromDishka[ItemService],
    mapper_service: FromDishka[MapperService],
    logger: Logger,
) -> None:
    """Re-apply mappers to the item and all of its descendants."""
    logger.info(f"Remap item hierarchy rooted at {item_uid}.")
    if item_service.get_optional(item_uid) is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail=f"Item {item_uid} not found"
        )
    mapper_service.remap_item_hierarchy(item_uid)
