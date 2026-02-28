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

"""FastAPI router for handling schemas."""
from http import HTTPStatus
from typing import List, Optional, Set
from uuid import UUID

from dishka.integrations.fastapi import (
    DishkaRoute,
    FromDishka,
)
from fastapi import APIRouter, Depends, HTTPException

from slidetap.model.schema.attribute_schema import AttributeSchema
from slidetap.model.schema.item_schema import ItemSchema
from slidetap.model.schema.root_schema import RootSchema
from slidetap.services import SchemaService
from slidetap.web.services.login_service import require_valid_token

schema_router = APIRouter(
    prefix="/api/schemas",
    tags=["schema"],
    route_class=DishkaRoute,
    dependencies=[Depends(require_valid_token)],
)


@schema_router.get("/root")
async def get_root_schema(
    schema_service: FromDishka[SchemaService],
) -> RootSchema:
    """Get the root schema.

    Returns
    ----------
    RootSchema
        The root schema
    """
    schema = schema_service.get_root()
    return schema


@schema_router.get("/attributes")
async def get_attribute_schemas(
    schema_service: FromDishka[SchemaService],
) -> List[AttributeSchema]:
    """Get attribute schemas for a schema.

    Returns
    ----------
    List[AttributeSchema]
        List of attribute schemas
    """
    schemas = schema_service.get_attributes(schema_service.get_root().uid)
    return list(schemas)


@schema_router.get("/attribute/{attribute_schema_uid}")
async def get_attribute_schema(
    attribute_schema_uid: UUID,
    schema_service: FromDishka[SchemaService],
) -> AttributeSchema:
    """Get attribute schema by ID.

    Parameters
    ----------
    attribute_schema_uid: UUID
        ID of the attribute schema

    Returns
    ----------
    AttributeSchema
        The requested attribute schema
    """
    schema = schema_service.get_attribute(attribute_schema_uid)
    if schema is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Attribute schema {attribute_schema_uid} not found",
        )
    return schema


@schema_router.get("/item/{item_schema_uid}")
async def get_item_schema(
    item_schema_uid: UUID,
    schema_service: FromDishka[SchemaService],
) -> Optional[ItemSchema]:
    """Get item schema by ID.

    Parameters
    ----------
    item_schema_uid: UUID
        ID of the item schema

    Returns
    ----------
    Optional[ItemSchema]
        The requested item schema, or None if not found
    """
    schema = schema_service.get_item(item_schema_uid)
    return schema


@schema_router.get("/item/{item_schema_uid}/hierarchy")
async def get_item_schema_hierarchy(
    item_schema_uid: UUID,
    schema_service: FromDishka[SchemaService],
) -> List[ItemSchema]:
    """Get item schema hierarchy.

    Parameters
    ----------
    item_schema_uid: UUID
        ID of the item schema

    Returns
    ----------
    List[ItemSchema]
        List of schemas in the hierarchy
    """
    schema = schema_service.get_item(item_schema_uid)
    if schema is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Item schema {item_schema_uid} not found",
        )

    schema_uids = schema_service.get_item_schema_hierarchy_recursive(schema)
    schemas = []
    for schema_uid in schema_uids:
        item_schema = schema_service.get_item(schema_uid)
        if item_schema:
            schemas.append(item_schema)

    return schemas
