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
from typing import Iterable, Optional
from uuid import UUID

from dishka.integrations.fastapi import (
    DishkaRoute,
    FromDishka,
)
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from slidetap.model import Dzi, Image
from slidetap.services import ImageService
from slidetap.web.services.login import require_login

image_router = APIRouter(
    prefix="/api/images",
    tags=["image"],
    route_class=DishkaRoute,
    dependencies=[Depends(require_login)],
)


@image_router.get("/thumbnails/{dataset_uid}")
async def get_thumbnails(
    dataset_uid: UUID,
    image_service: FromDishka[ImageService],
    batch_uid: Optional[UUID] = Query(None, alias="batchUid"),
) -> Iterable[Image]:
    """Get images that have thumbnails of specified dataset.

    Parameters
    ----------
    dataset_uid: UUID
        Id of dataset to get images that have thumbnails from.
    batch_uid: Optional[UUID]
        Optional batch UID to filter by

    Returns
    ----------
    Iterable[Image]
        List of images that have thumbnails.
    """
    images = image_service.get_images_with_thumbnail(dataset_uid, batch_uid)
    if images is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"No images found for dataset {dataset_uid}",
        )
    return images


@image_router.get("/image/{image_uid}/thumbnail")
async def get_thumbnail(
    image_uid: UUID,
    image_service: FromDishka[ImageService],
    width: int = Query(512),
    height: int = Query(512),
) -> Response:
    """Get thumbnail for specified image.

    Parameters
    ----------
    image_uid: UUID
        Id of image to get thumbnail of.
    width: int
        Width of thumbnail (default: 512)
    height: int
        Height of thumbnail (default: 512)

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


@image_router.get("/image/{image_uid}/dzi/{dzi_level}/{x}_{y}.{extension}")
async def get_tile_2d(
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
    tile = image_service.get_tile(image_uid, dzi_level, x, y, extension, None)
    if tile is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Tile not found for image {image_uid}",
        )
    return Response(content=tile, media_type="image/jpeg")


@image_router.get("/image/{image_uid}/dzi/{dzi_level}/{x}_{y}_{z}.{extension}")
async def get_tile_3d(
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
    tile = image_service.get_tile(image_uid, dzi_level, x, y, extension, z)
    if tile is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Tile not found for image {image_uid}",
        )
    return Response(content=tile, media_type="image/jpeg")


@image_router.get("/image/{image_uid}/dzi")
async def get_dzi(
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

    dzi = image_service.get_dzi(image_uid, base_url)
    if dzi is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"DZI metadata not found for image {image_uid}",
        )
    return dzi
