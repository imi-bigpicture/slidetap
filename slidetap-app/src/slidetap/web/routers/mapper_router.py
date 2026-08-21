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
from collections.abc import Iterable
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from dishka.integrations.fastapi import (
    DishkaRoute,
    FromDishka,
)
from fastapi import APIRouter, Depends, HTTPException

from slidetap.model.mapper import (
    Mapper,
    MapperCreate,
    MapperGroup,
    MapperGroupCreate,
    MappingItem,
    MappingItemCreate,
    UnmappedValue,
)
from slidetap.services import MapperService
from slidetap.web.routers.dependencies import create_logger_dependency
from slidetap.web.routers.responses import StatusResponse
from slidetap.web.services.login_service import require_valid_token

Logger = Annotated[logging.Logger, Depends(create_logger_dependency(__name__))]


mapper_router = APIRouter(
    prefix="/api/mappers",
    tags=["mapper"],
    route_class=DishkaRoute,
    dependencies=[Depends(require_valid_token)],
)


@mapper_router.post("/create")
async def create_mapper(
    mapper: MapperCreate,
    mapper_service: FromDishka[MapperService],
    logger: Logger,
) -> Mapper:
    """Create a new mapper.

    Parameters
    ----------
    mapper: MapperCreate
        Mapper data to create

    Returns
    ----------
    Mapper
        Created mapper
    """
    logger.debug("Creating mapper.")
    created_mapper = mapper_service.create_mapper(mapper)
    return created_mapper


@mapper_router.get("")
async def get_all_mappers(
    mapper_service: FromDishka[MapperService],
) -> Iterable[Mapper]:
    """Return all registered mappers.

    Returns
    ----------
    list[Mapper]
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
    if not mapper_service.delete_mapper(mapper_uid):
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Mapper {mapper_uid} not found",
        )
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
) -> Iterable[MappingItem]:
    """Get mappings for mapper.

    Parameters
    ----------
    mapper_uid: UUID
        ID of mapper

    Returns
    ----------
    list[MappingItem]
        List of mappings for the mapper
    """
    mappings = mapper_service.get_mappings_for_mapper(mapper_uid)
    return list(mappings)


@mapper_router.get("/project/{project_uid}/unmapped")
async def get_unmapped_values(
    project_uid: UUID,
    mapper_service: FromDishka[MapperService],
    batch_uid: UUID | None = None,
) -> list[UnmappedValue]:
    """Get the recorded values in a project that no mapping accounts for.

    Parameters
    ----------
    project_uid: UUID
        ID of project
    batch_uid: UUID | None
        Only values on items in this batch, when given

    Returns
    ----------
    list[UnmappedValue]
        Values with no mapping, most-carried first
    """
    return mapper_service.get_unmapped_values(project_uid, batch_uid)


@mapper_router.post("/mappings/create")
async def create_mapping(
    mapping: MappingItemCreate,
    mapper_service: FromDishka[MapperService],
    logger: Logger,
) -> MappingItem:
    """Create a new mapping.

    Parameters
    ----------
    mapping: MappingItemCreate
        Mapping data to create

    Returns
    ----------
    MappingItem
        Created mapping
    """
    logger.debug("Creating mapping.")
    created_mapping = mapper_service.create_mapping(mapping)
    return created_mapping


@mapper_router.post("/groups/create")
async def create_mapper_group(
    mapper_group: MapperGroupCreate,
    mapper_service: FromDishka[MapperService],
    logger: Logger,
) -> MapperGroup:
    """Create a new mapper group.

    Parameters
    ----------
    mapper_group: MapperGroupCreate
        Mapper group data to create

    Returns
    ----------
    MapperGroup
        Created mapper group
    """
    logger.debug("Creating mapper group.")
    created_group = mapper_service.get_or_create_mapper_group(
        mapper_group.name, mapper_group.default_enabled
    )
    return created_group


@mapper_router.post("/mappings/mapping/{mapping_uid}")
async def update_mapping(
    mapping_uid: UUID,
    mapping: MappingItem,
    mapper_service: FromDishka[MapperService],
    logger: Logger,
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
    logger.debug(f"Updating mapping {mapping_uid}")
    updated_mapping = mapper_service.update_mapping(mapping)
    return updated_mapping


@mapper_router.delete("/mappings/mapping/{mapping_uid}")
async def delete_mapping(
    mapping_uid: UUID,
    mapper_service: FromDishka[MapperService],
    logger: Logger,
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
        deleted = mapper_service.delete_mapping(mapping_uid)
    except ValueError as exception:
        logger.error(f"Failed to delete mapping {mapping_uid}", exc_info=True)
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Failed to delete mapping",
        ) from exception
    if not deleted:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Mapping {mapping_uid} not found",
        )
    return StatusResponse()


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


@mapper_router.get("/groups")
async def get_mapper_groups(
    mapper_service: FromDishka[MapperService],
) -> Iterable[MapperGroup]:
    """Get all mapper groups."""
    return mapper_service.get_all_mapper_groups()


@mapper_router.post("/groups/{group_uid}/mappers")
async def set_mappers_in_group(
    group_uid: UUID,
    mapper_uids: list[UUID],
    mapper_service: FromDishka[MapperService],
) -> MapperGroup:
    """Set the mappers that belong to a mapper group.

    Parameters
    ----------
    group_uid: UUID
        ID of group to update
    mapper_uids: list[UUID]
        IDs of the mappers the group should contain

    Returns
    ----------
    MapperGroup
        Updated mapper group
    """
    group = mapper_service.set_mappers_in_group(group_uid, mapper_uids)
    if group is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Mapper group {group_uid} or one of the given mappers not found",
        )
    return group
