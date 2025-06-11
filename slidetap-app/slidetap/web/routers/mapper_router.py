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

"""FastAPI router for handling mappers and mappings."""
import logging
from http import HTTPStatus
from typing import Dict, List
from uuid import UUID

from dishka.integrations.fastapi import (
    DishkaRoute,
    FromDishka,
)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from slidetap.model.mapper import Mapper, MapperGroup, MappingItem
from slidetap.services import MapperService
from slidetap.web.services.login import require_login


class StatusResponse(BaseModel):
    """Response model for status operations."""

    status: str = "ok"


class MapperGroupCreateRequest(BaseModel):
    """Request model for creating mapper groups."""

    name: str
    default_enabled: bool = False


mapper_router = APIRouter(
    prefix="/api/mappers",
    tags=["mapper"],
    route_class=DishkaRoute,
    dependencies=[Depends(require_login)],
)


@mapper_router.post("/create")
async def create_mapper(
    mapper: Mapper,
    mapper_service: FromDishka[MapperService],
) -> Mapper:
    """Create a new mapper.

    Parameters
    ----------
    mapper: Mapper
        Mapper data to create

    Returns
    ----------
    Mapper
        Created mapper
    """
    logging.debug("Creating mapper.")
    created_mapper = mapper_service.create_mapper(mapper)
    return created_mapper


@mapper_router.get("")
async def get_all_mappers(
    mapper_service: FromDishka[MapperService],
) -> List[Mapper]:
    """Return all registered mappers.

    Returns
    ----------
    List[Mapper]
        List of registered mappers
    """
    mappers = mapper_service.get_mappers()
    return list(mappers)


@mapper_router.get("/mapper/{mapper_uid}")
async def get_mapper(
    mapper_uid: UUID,
    mapper_service: FromDishka[MapperService],
) -> Mapper:
    """Return mapper specified by id.

    Parameters
    ----------
    mapper_uid: UUID
        ID of mapper to get

    Returns
    ----------
    Mapper
        The requested mapper
    """
    mapper = mapper_service.get_mapper(mapper_uid)
    if mapper is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Mapper {mapper_uid} not found",
        )
    return mapper


@mapper_router.delete("/mapper/{mapper_uid}")
async def delete_mapper(
    mapper_uid: UUID,
    mapper_service: FromDishka[MapperService],
) -> StatusResponse:
    """Delete mapper by ID.

    Parameters
    ----------
    mapper_uid: UUID
        ID of mapper to delete

    Returns
    ----------
    StatusResponse
        Status of the operation
    """
    mapper_service.delete_mapper(mapper_uid)
    return StatusResponse()


@mapper_router.post("/mapper/{mapper_uid}")
async def update_mapper(
    mapper_uid: UUID,
    mapper: Mapper,
    mapper_service: FromDishka[MapperService],
) -> Mapper:
    """Update mapper.

    Parameters
    ----------
    mapper_uid: UUID
        ID of mapper to update
    mapper: Mapper
        Updated mapper data

    Returns
    ----------
    Mapper
        Updated mapper
    """
    updated_mapper = mapper_service.update_mapper(mapper)
    return updated_mapper


@mapper_router.get("/mapper/{mapper_uid}/mapping")
async def get_mappings(
    mapper_uid: UUID,
    mapper_service: FromDishka[MapperService],
) -> List[MappingItem]:
    """Get mappings for mapper.

    Parameters
    ----------
    mapper_uid: UUID
        ID of mapper

    Returns
    ----------
    List[MappingItem]
        List of mappings for the mapper
    """
    mappings = mapper_service.get_mappings_for_mapper(mapper_uid)
    return list(mappings)


@mapper_router.get("/mapper/{mapper_uid}/attributes")
async def get_mapping_attributes(
    mapper_uid: UUID,
    mapper_service: FromDishka[MapperService],
) -> List[MappingItem]:
    """Get mapping attributes for mapper.

    Parameters
    ----------
    mapper_uid: UUID
        ID of mapper

    Returns
    ----------
    List[MappingItem]
        List of mapping attributes
    """
    mappings = mapper_service.get_mappings_for_mapper(mapper_uid)
    return list(mappings)


@mapper_router.post("/mappings/create")
async def create_mapping(
    mapping: MappingItem,
    mapper_service: FromDishka[MapperService],
) -> MappingItem:
    """Create a new mapping.

    Parameters
    ----------
    mapping: MappingItem
        Mapping data to create

    Returns
    ----------
    MappingItem
        Created mapping
    """
    logging.debug("Creating mapping.")
    created_mapping = mapper_service.create_mapping(mapping)
    return created_mapping


@mapper_router.post("/groups/create")
async def create_mapper_group(
    mapper_group_request: MapperGroupCreateRequest,
    mapper_service: FromDishka[MapperService],
) -> MapperGroup:
    """Create a new mapper group.

    Parameters
    ----------
    mapper_group_request: MapperGroupCreateRequest
        Mapper group data to create

    Returns
    ----------
    MapperGroup
        Created mapper group
    """
    logging.debug("Creating mapper group.")
    mapper_group = mapper_service.get_or_create_mapper_group(
        mapper_group_request.name, mapper_group_request.default_enabled
    )
    return mapper_group


@mapper_router.post("/mappings/mapping/{mapping_uid}")
async def update_mapping(
    mapping_uid: UUID,
    mapping: MappingItem,
    mapper_service: FromDishka[MapperService],
) -> MappingItem:
    """Update mapping.

    Parameters
    ----------
    mapping_uid: UUID
        ID of mapping to update
    mapping: MappingItem
        Updated mapping data

    Returns
    ----------
    MappingItem
        Updated mapping
    """
    logging.debug(f"Updating mapping {mapping_uid}")
    updated_mapping = mapper_service.update_mapping(mapping)
    return updated_mapping


@mapper_router.delete("/mappings/mapping/{mapping_uid}")
async def delete_mapping(
    mapping_uid: UUID,
    mapper_service: FromDishka[MapperService],
) -> StatusResponse:
    """Delete mapping.

    Parameters
    ----------
    mapping_uid: UUID
        ID of mapping to delete

    Returns
    ----------
    StatusResponse
        Status of the operation
    """
    try:
        mapper = mapper_service.delete_mapping(mapping_uid)
        if mapper is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Mapping {mapping_uid} not found",
            )
        return StatusResponse()
    except ValueError as e:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(e),
        )


@mapper_router.get("/mappings/mapping/{mapping_uid}")
async def get_mapping(
    mapping_uid: UUID,
    mapper_service: FromDishka[MapperService],
) -> MappingItem:
    """Get mapping by ID.

    Parameters
    ----------
    mapping_uid: UUID
        ID of mapping to get

    Returns
    ----------
    MappingItem
        The requested mapping
    """
    mapping = mapper_service.get_mapping(mapping_uid)
    if mapping is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Mapping {mapping_uid} not found",
        )
    return mapping


@mapper_router.get("/mapper/{mapper_uid}/unmapped")
async def get_unmapped(mapper_uid: UUID) -> Dict:
    """Get unmapped values from mapper.

    Parameters
    ----------
    mapper_uid: UUID
        ID of mapper

    Returns
    ----------
    Dict
        Unmapped values (not implemented)
    """
    raise HTTPException(
        status_code=HTTPStatus.NOT_IMPLEMENTED,
        detail="Get unmapped functionality not implemented",
    )


@mapper_router.get("/groups")
async def get_mapper_groups(
    mapper_service: FromDishka[MapperService],
):
    """Get all mapper groups.

    Returns
    ----------
    List[MapperGroup]
        List of all mapper groups
    """
    mapper_groups = mapper_service.get_all_mapper_groups()
    return list(mapper_groups)
