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

"""FastAPI router for handling schemas.

A project is on the root schema it was created with, and several can be
provided. What is looked up within a root takes the root of the project as
``rootSchemaUid``; without it, the root of new projects.
"""

from collections.abc import Iterable
from http import HTTPStatus
from uuid import UUID

from dishka.integrations.fastapi import (
    DishkaRoute,
    FromDishka,
)
from fastapi import APIRouter, Depends, HTTPException, Query

from slidetap.model.schema.attribute_schema import AnyAttributeSchema
from slidetap.model.schema.item_schema import AnyItemSchema
from slidetap.model.schema.root_schema import RootSchema
from slidetap.model.schema.root_schema_summary import RootSchemaSummary
from slidetap.services import SchemaService
from slidetap.web.services.login_service import require_valid_token

schema_router = APIRouter(
    prefix="/api/schemas",
    tags=["schema"],
    route_class=DishkaRoute,
    dependencies=[Depends(require_valid_token)],
)


@schema_router.get("/roots")
async def get_root_schemas(
    schema_service: FromDishka[SchemaService],
) -> list[RootSchemaSummary]:
    """Get every root schema the application provides.

    Returns
    ----------
    list[RootSchemaSummary]
        The roots, and which of them new projects are created with.
    """
    return [
        RootSchemaSummary(
            uid=root.uid,
            name=root.schema.name,
            new_projects=root.uid == schema_service.default_root.uid,
        )
        for root in schema_service.roots.values()
    ]


@schema_router.get("/root/{root_schema_uid}")
async def get_root_schema_by_uid(
    root_schema_uid: UUID,
    schema_service: FromDishka[SchemaService],
) -> RootSchema:
    """Get a root schema by ID.

    Parameters
    ----------
    root_schema_uid: UUID
        ID of the root schema, such as the root of a project.

    Returns
    ----------
    RootSchema
        The requested root schema
    """
    return schema_service.get_root(root_schema_uid).schema


@schema_router.get("/root")
async def get_root_schema(
    schema_service: FromDishka[SchemaService],
    root_schema_uid: UUID | None = Query(None, alias="rootSchemaUid"),
) -> RootSchema:
    """Get a root schema.

    Parameters
    ----------
    root_schema_uid: UUID | None
        The root of a project. Without it, the root of new projects.

    Returns
    ----------
    RootSchema
        The root schema
    """
    return (
        schema_service.get_root(root_schema_uid)
        if root_schema_uid is not None
        else schema_service.default_root
    ).schema


@schema_router.get("/attributes")
async def get_attribute_schemas(
    schema_service: FromDishka[SchemaService],
    root_schema_uid: UUID | None = Query(None, alias="rootSchemaUid"),
) -> Iterable[AnyAttributeSchema]:
    """Get the attribute schemas of a root.

    Parameters
    ----------
    root_schema_uid: UUID | None
        The root of a project. Without it, the root of new projects.

    Returns
    ----------
    list[AnyAttributeSchema]
        List of attribute schemas
    """
    root = (
        schema_service.get_root(root_schema_uid)
        if root_schema_uid is not None
        else schema_service.default_root
    )
    return list(root.get_attributes())


@schema_router.get("/attribute/{attribute_schema_uid}")
async def get_attribute_schema(
    attribute_schema_uid: UUID,
    schema_service: FromDishka[SchemaService],
) -> AnyAttributeSchema:
    """Get attribute schema by ID.

    An attribute schema uid means one definition in every root, so it is looked
    up across them.

    Parameters
    ----------
    attribute_schema_uid: UUID
        ID of the attribute schema

    Returns
    ----------
    AnyAttributeSchema
        The requested attribute schema
    """
    try:
        # Private attributes are held apart from the public ones, and both are
        # reachable from the schemas that use them.
        return schema_service.get_any_attribute(attribute_schema_uid)
    except (KeyError, ValueError) as exception:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Attribute schema {attribute_schema_uid} not found",
        ) from exception


@schema_router.get("/item/{item_schema_uid}")
async def get_item_schema(
    item_schema_uid: UUID,
    schema_service: FromDishka[SchemaService],
    root_schema_uid: UUID | None = Query(None, alias="rootSchemaUid"),
) -> AnyItemSchema | None:
    """Get item schema by ID.

    Parameters
    ----------
    item_schema_uid: UUID
        ID of the item schema
    root_schema_uid: UUID | None
        The root to look the item schema up in, as the same ID can have
        another definition in another root. Without it, the root of new
        projects.

    Returns
    ----------
    AnyItemSchema | None
        The requested item schema, or None if not found
    """
    root = (
        schema_service.get_root(root_schema_uid)
        if root_schema_uid is not None
        else schema_service.default_root
    )
    return root.items.get(item_schema_uid)


@schema_router.get("/item/{item_schema_uid}/hierarchy")
async def get_item_schema_hierarchy(
    item_schema_uid: UUID,
    schema_service: FromDishka[SchemaService],
    root_schema_uid: UUID | None = Query(None, alias="rootSchemaUid"),
) -> Iterable[AnyItemSchema]:
    """Get item schema hierarchy.

    Parameters
    ----------
    item_schema_uid: UUID
        ID of the item schema
    root_schema_uid: UUID | None
        The root to look the item schema up in. Without it, the root of new
        projects.

    Returns
    ----------
    list[AnyItemSchema]
        List of schemas in the hierarchy
    """
    root = (
        schema_service.get_root(root_schema_uid)
        if root_schema_uid is not None
        else schema_service.default_root
    )
    schema = root.items.get(item_schema_uid)
    if schema is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Item schema {item_schema_uid} not found",
        )

    schema_uids = root.get_item_schema_hierarchy_recursive(schema)
    schemas = []
    for schema_uid in schema_uids:
        item_schema = root.items.get(schema_uid)
        if item_schema:
            schemas.append(item_schema)

    return schemas
