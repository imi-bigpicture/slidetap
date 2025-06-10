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

from fastapi import HTTPException
from pydantic import BaseModel

from slidetap.model.mapper import Mapper, MapperGroup, MappingItem
from slidetap.services import AttributeService, MapperService, SchemaService
from slidetap.web.routers.router import SecuredRouter


class StatusResponse(BaseModel):
    """Response model for status operations."""

    status: str = "ok"


class MapperGroupCreateRequest(BaseModel):
    """Request model for creating mapper groups."""

    name: str
    default_enabled: bool = False


class MapperRouter(SecuredRouter):
    """FastAPI router for mappers."""

    def __init__(
        self,
        mapper_service: MapperService,
        attribute_service: AttributeService,
        schema_service: SchemaService,
    ):
        self._mapper_service = mapper_service
        self._attribute_service = attribute_service
        self._schema_service = schema_service
        self._logger = logging.getLogger(__name__)
        super().__init__()

        # Register routes
        self._register_routes()

    def _register_routes(self):
        """Register all mapper routes."""

        @self.router.post("/create")
        async def create_mapper(mapper: Mapper, user=self.auth_dependency()) -> Mapper:
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
            self._logger.debug("Creating mapper.")
            created_mapper = self._mapper_service.create_mapper(mapper)
            return created_mapper

        @self.router.get("")
        async def get_all_mappers(user=self.auth_dependency()) -> List[Mapper]:
            """Return all registered mappers.

            Returns
            ----------
            List[Mapper]
                List of registered mappers
            """
            mappers = self._mapper_service.get_mappers()
            return list(mappers)

        @self.router.get("/mapper/{mapper_uid}")
        async def get_mapper(mapper_uid: UUID, user=self.auth_dependency()) -> Mapper:
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
            mapper = self._mapper_service.get_mapper(mapper_uid)
            if mapper is None:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Mapper {mapper_uid} not found",
                )
            return mapper

        @self.router.delete("/mapper/{mapper_uid}")
        async def delete_mapper(
            mapper_uid: UUID, user=self.auth_dependency()
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
            self._mapper_service.delete_mapper(mapper_uid)
            return StatusResponse()

        @self.router.post("/mapper/{mapper_uid}")
        async def update_mapper(
            mapper_uid: UUID, mapper: Mapper, user=self.auth_dependency()
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
            updated_mapper = self._mapper_service.update_mapper(mapper)
            return updated_mapper

        @self.router.get("/mapper/{mapper_uid}/mapping")
        async def get_mappings(
            mapper_uid: UUID, user=self.auth_dependency()
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
            mappings = self._mapper_service.get_mappings_for_mapper(mapper_uid)
            return list(mappings)

        @self.router.get("/mapper/{mapper_uid}/attributes")
        async def get_mapping_attributes(
            mapper_uid: UUID, user=self.auth_dependency()
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
            mappings = self._mapper_service.get_mappings_for_mapper(mapper_uid)
            return list(mappings)

        @self.router.post("/mappings/create")
        async def create_mapping(
            mapping: MappingItem, user=self.auth_dependency()
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
            self._logger.debug("Creating mapping.")
            created_mapping = self._mapper_service.create_mapping(mapping)
            return created_mapping

        @self.router.post("/groups/create")
        async def create_mapper_group(
            mapper_group_request: MapperGroupCreateRequest, user=self.auth_dependency()
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
            self._logger.debug("Creating mapper group.")
            mapper_group = self._mapper_service.get_or_create_mapper_group(
                mapper_group_request.name, mapper_group_request.default_enabled
            )
            return mapper_group

        @self.router.post("/mappings/mapping/{mapping_uid}")
        async def update_mapping(
            mapping_uid: UUID, mapping: MappingItem, user=self.auth_dependency()
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
            self._logger.debug(f"Updating mapping {mapping_uid}")
            updated_mapping = self._mapper_service.update_mapping(mapping)
            return updated_mapping

        @self.router.delete("/mappings/mapping/{mapping_uid}")
        async def delete_mapping(
            mapping_uid: UUID, user=self.auth_dependency()
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
                mapper = self._mapper_service.delete_mapping(mapping_uid)
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

        @self.router.get("/mappings/mapping/{mapping_uid}")
        async def get_mapping(
            mapping_uid: UUID, user=self.auth_dependency()
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
            mapping = self._mapper_service.get_mapping(mapping_uid)
            if mapping is None:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Mapping {mapping_uid} not found",
                )
            return mapping

        @self.router.get("/mapper/{mapper_uid}/unmapped")
        async def get_unmapped(mapper_uid: UUID, user=self.auth_dependency()) -> Dict:
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

        @self.router.get("/groups")
        async def get_mapper_groups(user=self.auth_dependency()):
            """Get all mapper groups.

            Returns
            ----------
            List[MapperGroup]
                List of all mapper groups
            """
            mapper_groups = self._mapper_service.get_all_mapper_groups()
            return list(mapper_groups)
