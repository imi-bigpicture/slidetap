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

"""FastAPI router for handling attributes."""
import logging
from typing import Annotated, Dict, Iterable
from uuid import UUID

from dishka.integrations.fastapi import (
    DishkaRoute,
    FromDishka,
)
from fastapi import APIRouter, Depends, HTTPException

from slidetap.model import MappingItem
from slidetap.model.attribute import AnyAttribute, Attribute, attribute_factory
from slidetap.services import (
    AttributeService,
    MapperService,
    SchemaService,
)
from slidetap.web.routers.dependencies import create_logger_dependency
from slidetap.web.services.login_service import require_valid_token_and_refresh

attribute_router = APIRouter(
    prefix="/api/attributes",
    tags=["attribute"],
    route_class=DishkaRoute,
    dependencies=[Depends(require_valid_token_and_refresh)],
)

Logger = Annotated[logging.Logger, Depends(create_logger_dependency(__name__))]


@attribute_router.get("/attribute/{attribute_uid}")
async def get_attribute(
    attribute_uid: UUID,
    attribute_service: FromDishka[AttributeService],
    logger: Logger,
) -> Attribute:
    """Get attribute by ID."""
    logger.debug(f"Get attribute {attribute_uid}.")
    attribute = attribute_service.get(attribute_uid)
    if attribute is None:
        logger.error(f"Attribute {attribute_uid} not found.")
        raise HTTPException(status_code=404, detail="Attribute not found")
    return attribute


@attribute_router.post("/attribute/{attribute_uid}")
async def update_attribute(
    attribute_uid: UUID,
    attribute: AnyAttribute,
    attribute_service: FromDishka[AttributeService],
    logger: Logger,
) -> Attribute:
    """Update attribute."""
    logger.debug(f"Update attribute {attribute_uid}.")
    updated_attribute = attribute_service.update(attribute)
    if updated_attribute is None:
        raise HTTPException(status_code=404, detail="Attribute not found")
    return attribute


@attribute_router.post("/create/{attribute_schema_uid}")
async def create_attribute(
    attribute_schema_uid: UUID,
    attribute_data: Dict,
    attribute_service: FromDishka[AttributeService],
    schema_service: FromDishka[SchemaService],
    logger: Logger,
) -> Attribute:
    """Create attribute."""
    logger.debug("Create attribute.")
    attribute_schema = schema_service.get_attribute(attribute_schema_uid)
    assert attribute_schema is not None
    attribute = attribute_factory(attribute_data)
    attribute = attribute_service.create(attribute)
    return attribute


@attribute_router.get("/attribute/{attribute_uid}/mapping")
async def get_mapping(
    attribute_uid: UUID,
    attribute_service: FromDishka[AttributeService],
    mapper_service: FromDishka[MapperService],
    logger: Logger,
) -> MappingItem:
    """Get mapping for attribute."""
    logger.debug(f"Get mapping for attribute {attribute_uid}.")
    attribute = attribute_service.get(attribute_uid)
    if attribute is None or attribute.mappable_value is None:
        raise HTTPException(status_code=404, detail="Attribute not found")
    if attribute.mapping_item_uid is None:
        mapping_item = mapper_service.get_mapping_for_attribute(attribute)
    else:
        mapping_item = mapper_service.get_mapping(attribute.mapping_item_uid)
    if mapping_item is None:
        raise HTTPException(status_code=404, detail="Mapping not found")
    return mapping_item


@attribute_router.get("/schema/{attribute_schema_uid}")
async def get_attributes_for_schema(
    attribute_schema_uid: UUID,
    attribute_service: FromDishka[AttributeService],
) -> Iterable[Attribute]:
    """Get attributes for schema."""
    attributes = attribute_service.get_for_schema(attribute_schema_uid)
    return attributes
