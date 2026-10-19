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

"""FastAPI router for accessing image data."""

from http import HTTPStatus
from uuid import UUID

from dishka.integrations.fastapi import (
    DishkaRoute,
    FromDishka,
)
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from wsidicom.errors import WsiDicomNotFoundError, WsiDicomOutOfBoundsError

from slidetap.model import Dzi
from slidetap.services import ImageService
from slidetap.web.services.login_service import require_valid_token

image_router = APIRouter(
    prefix="/api/images",
    tags=["image"],
    route_class=DishkaRoute,
    dependencies=[Depends(require_valid_token)],
)

MAX_THUMBNAIL_SIZE = 2048
"""The largest width or height, in pixels, a thumbnail is made at."""


@image_router.get("/image/{image_uid}/thumbnail")
def get_thumbnail(
    image_uid: UUID,
    image_service: FromDishka[ImageService],
    width: int = Query(512, ge=1, le=MAX_THUMBNAIL_SIZE),
    height: int = Query(512, ge=1, le=MAX_THUMBNAIL_SIZE),
) -> Response:
    """Get thumbnail for specified image.

    Parameters
    ----------
    image_uid: UUID
        Id of image to get thumbnail of.
    width: int
        Width of thumbnail (default: 512, at most ``MAX_THUMBNAIL_SIZE``)
    height: int
        Height of thumbnail (default: 512, at most ``MAX_THUMBNAIL_SIZE``)

    Returns
    ----------
    Response
        Response with thumbnail as bytes.
    """
    thumbnail = image_service.get_thumbnail(image_uid, width, height, "png")
    if thumbnail is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Thumbnail not found for image {image_uid}",
        )
    return Response(content=thumbnail, media_type="image/png")


def _read_tile(
    image_service: ImageService,
    image_uid: UUID,
    dzi_level: int,
    x: int,
    y: int,
    extension: str,
    z: int | None,
) -> Response:
    """Read a tile, answering not found for an image without files to read
    and for a tile outside the image."""
    try:
        tile = image_service.get_tile(image_uid, dzi_level, x, y, extension, z)
    except (ValueError, WsiDicomNotFoundError, WsiDicomOutOfBoundsError) as exception:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Tile not found for image {image_uid}",
        ) from exception
    return Response(content=tile, media_type="image/jpeg")


# The coordinates are matched as integers, so that a 3D tile name such as
# ``1_2_3.jpeg`` does not also match the 2D route with ``x`` as ``1_2``.
@image_router.get("/image/{image_uid}/dzi/{dzi_level}/{x:int}_{y:int}.{extension}")
def get_tile_2d(
    image_uid: UUID,
    dzi_level: int,
    x: int,
    y: int,
    extension: str,
    image_service: FromDishka[ImageService],
) -> Response:
    """Get 2D tile for specified image.

    Parameters
    ----------
    image_uid: UUID
        Id of image
    dzi_level: int
        DZI level
    x: int
        X coordinate
    y: int
        Y coordinate
    extension: str
        File extension

    Returns
    ----------
    Response
        Response with tile as bytes.
    """
    return _read_tile(image_service, image_uid, dzi_level, x, y, extension, None)


@image_router.get(
    "/image/{image_uid}/dzi/{dzi_level}/{x:int}_{y:int}_{z:int}.{extension}"
)
def get_tile_3d(
    image_uid: UUID,
    dzi_level: int,
    x: int,
    y: int,
    z: int,
    extension: str,
    image_service: FromDishka[ImageService],
) -> Response:
    """Get 3D tile for specified image.

    Parameters
    ----------
    image_uid: UUID
        Id of image
    dzi_level: int
        DZI level
    x: int
        X coordinate
    y: int
        Y coordinate
    z: int
        Z coordinate
    extension: str
        File extension

    Returns
    ----------
    Response
        Response with tile as bytes.
    """
    return _read_tile(image_service, image_uid, dzi_level, x, y, extension, z)


@image_router.get("/image/{image_uid}/dzi")
def get_dzi(
    image_uid: UUID,
    image_service: FromDishka[ImageService],
) -> Dzi:
    """Get DZI metadata for specified image.

    Parameters
    ----------
    image_uid: UUID
        Id of image

    Returns
    ----------
    Dzi
        DZI metadata for the image.
    """
    base_url = "/api/images/image/" + str(image_uid) + "/dzi/"

    try:
        return image_service.get_dzi(image_uid, base_url)
    except ValueError as exception:
        # The image has no files to read.
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"DZI metadata not found for image {image_uid}",
        ) from exception
