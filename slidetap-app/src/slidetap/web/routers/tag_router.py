#    Copyright 2025 SECTRA AB
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

"""FastAPI router for handling tags."""
from http import HTTPStatus
from typing import List
from uuid import UUID

from dishka.integrations.fastapi import (
    DishkaRoute,
    FromDishka,
)
from fastapi import APIRouter, Depends, HTTPException

from slidetap.model import Dataset
from slidetap.model.tag import Tag
from slidetap.services import DatasetService
from slidetap.services.tag_service import TagService
from slidetap.web.services.login_service import require_valid_token_and_refresh

tag_router = APIRouter(
    prefix="/api/tags",
    tags=["tag"],
    route_class=DishkaRoute,
    dependencies=[Depends(require_valid_token_and_refresh)],
)


@tag_router.get("")
async def get_tags(tag_service: FromDishka[TagService]) -> List[Tag]:
    """Get all tags.

    Returns
    ----------
    List[Tag]
        List of all Tag
    """
    return tag_service.get_all()


@tag_router.post("/tag/{tag_uid}")
async def update_tag(tag_service: FromDishka[TagService], tag: Tag) -> Tag:
    """Update tags for an item.

    Parameters
    ----------
    item_id : UUID
        The ID of the item to update tags for.
    tags : List[Tag]
        The list of tags to update for the item.
    """
    return tag_service.update(tag)
