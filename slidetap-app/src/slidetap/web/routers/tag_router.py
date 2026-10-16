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

from collections.abc import Iterable
from http import HTTPStatus
from uuid import UUID

from dishka.integrations.fastapi import (
    DishkaRoute,
    FromDishka,
)
from fastapi import APIRouter, Depends, HTTPException

from slidetap.model.tag import Tag
from slidetap.services.tag_service import TagService
from slidetap.web.services.login_service import require_valid_token

tag_router = APIRouter(
    prefix="/api/tags",
    tags=["tag"],
    route_class=DishkaRoute,
    dependencies=[Depends(require_valid_token)],
)


@tag_router.get("")
def get_tags(tag_service: FromDishka[TagService]) -> Iterable[Tag]:
    """Get all tags.

    Returns
    ----------
    list[Tag]
        List of all Tag
    """
    return tag_service.get_all()


@tag_router.post("/tag/{tag_uid}")
def update_tag(tag_uid: UUID, tag_service: FromDishka[TagService], tag: Tag) -> Tag:
    """Update a tag.

    Parameters
    ----------
    tag_uid : UUID
        The uid of the tag to update, which the tag in the body must have.
    tag : Tag
        The tag as it is to be stored.
    """
    if tag.uid != tag_uid:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=f"Tag uid {tag.uid} does not match path uid {tag_uid}",
        )
    return tag_service.update(tag)
