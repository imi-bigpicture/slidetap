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

from fastapi import HTTPException, Query
from pydantic import BaseModel

from slidetap.model import ImageStatus, TableRequest
from slidetap.model.item import AnyItem, Image, ImageGroup, Item, item_factory
from slidetap.model.item_reference import ItemReference
from slidetap.services import (
    DatabaseService,
    ItemService,
    SchemaService,
    ValidationService,
)
from slidetap.web.routers.router import SecuredRouter
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


class ItemRouter(SecuredRouter):
    """FastAPI router for items."""

    def __init__(
        self,
        item_service: ItemService,
        schema_service: SchemaService,
        validation_service: ValidationService,
        database_service: DatabaseService,
        metadata_export_service: MetadataExportService,
        image_import_service: ImageImportService,
        image_export_service: ImageExportService,
    ):
        self._item_service = item_service
        self._schema_service = schema_service
        self._validation_service = validation_service
        self._database_service = database_service
        self._metadata_export_service = metadata_export_service
        self._image_import_service = image_import_service
        self._image_export_service = image_export_service
        self._logger = logging.getLogger(__name__)
        super().__init__()

        # Register routes
        self._register_routes()

    def _register_routes(self):
        """Register all item routes."""

        @self.router.get("/item/{item_uid}")
        async def get_item(item_uid: UUID, user=self.auth_dependency()) -> AnyItem:
            """Get item by ID.

            Parameters
            ----------
            item_uid: UUID
                ID of the item

            Returns
            ----------
            Item
                The requested item
            """
            self._logger.debug(f"Get item {item_uid}.")
            item = self._item_service.get(item_uid)
            if item is None:
                self._logger.error(f"Item {item_uid} not found.")
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Item {item_uid} not found",
                )
            return item

        @self.router.get("/item//{item_uid}/preview")
        async def preview_item(
            item_uid: UUID, user=self.auth_dependency()
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
            self._logger.debug(f"Preview item {item_uid}.")
            preview = self._metadata_export_service.preview_item(item_uid)
            if preview is None:
                self._logger.error(f"Item {item_uid} not found.")
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Item {item_uid} not found",
                )
            return PreviewResponse(preview=preview)

        @self.router.post("/item//{item_uid}/select")
        async def select_item(
            item_uid: UUID, value: bool = Query(...), user=self.auth_dependency()
        ):
            """Select or de-select item.

            Parameters
            ----------
            item_uid: UUID
                ID of item to select
            value: bool
                Selection value (true to select, false to deselect)

            """
            self._logger.debug(f"Select item {item_uid}.")
            item = self._item_service.select(item_uid, value)
            if item is None:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Item {item_uid} not found",
                )

        @self.router.post("/item//{item_uid}")
        async def save_item(
            item_uid: UUID, item: Item, user=self.auth_dependency()
        ) -> Item:
            """Update item with specified id.

            Parameters
            ----------
            item_uid: UUID
                ID of item to update
            item: Item
                Item data to update

            Returns
            ----------
            Item
                Updated item
            """
            self._logger.debug(f"Save item {item_uid}.")
            updated_item = self._item_service.update(item)
            if updated_item is None:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Item {item_uid} not found",
                )
            return updated_item

        @self.router.post("/add")
        async def add_item(
            item_data: Dict,
            user=self.auth_dependency(),
        ) -> AnyItem:
            """Add item to project.

            Parameters
            ----------
            schema_uid: UUID
                Schema UID for the item
            project_uid: UUID
                Project UID to add item to
            item_data: Dict
                Item data

            Returns
            ----------
            Item
                Created item
            """
            self._logger.debug("Add item.")
            item = item_factory(item_data)
            created_item = self._item_service.add(item)
            return created_item

        @self.router.post("/create")
        async def create_item(
            schema_uid: UUID = Query(..., alias="schemaUid"),
            project_uid: UUID = Query(..., alias="projectUid"),
            batch_uid: UUID = Query(..., alias="batchUid"),
            user=self.auth_dependency(),
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
            Item
                Created item
            """
            self._logger.debug("Create item.")
            item = self._item_service.create(schema_uid, project_uid, batch_uid)
            if item is None:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail="Failed to create item",
                )
            return item

        @self.router.post("/item/{item_uid}/copy")
        async def copy_item(item_uid: UUID, user=self.auth_dependency()) -> AnyItem:
            """Copy item with specified id.

            Parameters
            ----------
            item_uid: UUID
                ID of item to copy

            Returns
            ----------
            Item
                Copied item
            """
            self._logger.debug(f"Copy item {item_uid}.")
            copied_item = self._item_service.copy(item_uid)
            if copied_item is None:
                self._logger.error(f"Item {item_uid} not found.")
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Item {item_uid} not found",
                )
            return copied_item

        @self.router.get("")
        @self.router.post("")
        async def get_items(
            dataset_uid: UUID = Query(..., alias="datasetUid"),
            item_schema_uid: UUID = Query(..., alias="itemSchemaUid"),
            batch_uid: Optional[UUID] = Query(None, alias="batchUid"),
            table_request: Optional[TableRequest] = None,
            user=self.auth_dependency(),
        ) -> ItemsResponse:
            """Get items of specified type from dataset.

            Parameters
            ----------
            dataset_uid: UUID
                ID of dataset to get items from
            item_schema_uid: UUID
                Item schema to get
            batch_uid: Optional[UUID]
                Optional batch UID filter
            table_request: Optional[TableRequest]
                Table request parameters (for POST requests)

            Returns
            ----------
            ItemsResponse
                Items and count
            """
            if table_request is None:
                table_request = TableRequest()

            items = self._item_service.get_for_schema(
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
            )
            count = self._item_service.get_count_for_schema(
                item_schema_uid,
                dataset_uid,
                batch_uid,
                table_request.identifier_filter,
                table_request.attribute_filters,
                table_request.included,
                table_request.valid,
                table_request.status_filter,
            )
            return ItemsResponse(items=list(items), count=count)

        @self.router.get("/references")
        async def get_references(
            dataset_uid: UUID = Query(..., alias="datasetUid"),
            item_schema_uid: UUID = Query(..., alias="itemSchemaUid"),
            batch_uid: Optional[UUID] = Query(None, alias="batchUid"),
            user=self.auth_dependency(),
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
            Dict[str, Item]
                Dictionary of item references keyed by UID
            """
            self._logger.debug(f"Get items of schema {item_schema_uid}.")
            item_schema = self._schema_service.get_item(item_schema_uid)
            if item_schema is None:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Item schema {item_schema_uid} not found",
                )
            items = self._item_service.get_references_for_schema(
                item_schema_uid, dataset_uid, batch_uid
            )
            return {str(item.uid): item for item in items}

        @self.router.get("/item/{item_uid}/images")
        async def get_images_for_item(
            item_uid: UUID,
            group_by_schema_uid: UUID = Query(..., alias="groupBySchemaUid"),
            image_schema_uid: Optional[UUID] = Query(None, alias="imageSchemaUid"),
            user=self.auth_dependency(),
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
            List[Dict]
                List of image groups
            """
            self._logger.debug(
                f"Get images for item {item_uid} grouped by {group_by_schema_uid}."
            )
            groups = self._item_service.get_images_for_item(
                item_uid, group_by_schema_uid, image_schema_uid
            )
            return groups

        @self.router.post("/retry")
        async def retry(image_uids: List[UUID], user=self.auth_dependency()):
            """Retry processing for failed images.

            Parameters
            ----------
            image_uids: List[UUID]
                List of image UIDs to retry
            """
            for image_uid in image_uids:
                self._retry_image(image_uid)

    def _retry_image(self, image_uid: UUID) -> None:
        """Retry processing for a failed image."""
        with self._database_service.get_session() as session:
            image = self._database_service.get_image(session, image_uid)
            if image is None:
                raise ValueError(f"Image {image_uid} does not exist.")
            if image.batch is None:
                raise ValueError(f"Image {image_uid} does not belong to a batch.")
            image.status_message = ""
            if image.status == ImageStatus.DOWNLOADING_FAILED:
                image.reset_as_not_started()
                self._image_import_service.redo_image_download(image.model)
            elif image.status == ImageStatus.PRE_PROCESSING_FAILED:
                image.reset_as_downloaded()
                self._image_import_service.redo_image_pre_processing(image.model)
            elif image.status == ImageStatus.POST_PROCESSING_FAILED:
                image.reset_as_pre_processed()
                self._image_export_service.re_export(image.batch.model, image.model)
