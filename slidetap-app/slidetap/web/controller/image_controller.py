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

"""Controller for accessing image data."""
import io
from typing import Optional
from uuid import UUID

from flask import Blueprint, request, send_file, url_for
from flask.wrappers import Response

from slidetap.services import ImageService
from slidetap.web.controller import Controller
from slidetap.web.services import LoginService


class ImageController(Controller):
    def __init__(
        self,
        login_service: LoginService,
        image_service: ImageService,
    ):
        super().__init__(login_service, Blueprint("image", __name__))
        self._image_service = image_service

        @self.blueprint.route("/thumbnails/<uuid:dataset_uid>", methods=["GET"])
        def get_thumbnails(dataset_uid: UUID) -> Response:
            """Get images that have thumbnails of specified project.

            Parameters
            ----------
            project_uid: UUID
                Id of project to get images that have thumbnails from.

            Returns
            ----------
            Response
                Json-response of images that have thumbnails.
            """
            if "batchUid" in request.args:
                batch_uid = UUID(request.args["batchUid"])
            else:
                batch_uid = None
            images = image_service.get_images_with_thumbnail(dataset_uid, batch_uid)
            if images is None:
                return self.return_not_found()
            return self.return_json(
                [image.model_dump(mode="json", by_alias=True) for image in images]
            )

        @self.blueprint.route("/<uuid:image_uid>/thumbnail", methods=["GET"])
        def get_thumbnail(image_uid: UUID) -> Response:
            """Get thuembnail for specified image.

            Parameters
            ----------
            project_uid: UUID
                Id of project.
            image_uid: UUID
                Id of image to get thumbnail of.

            Returns
            ----------
            Response
                Response with thumbnail as bytes.
            """
            width = int(request.args.get("width", 512))
            height = int(request.args.get("height", 512))
            thumbnail = self._image_service.get_thumbnail(
                image_uid, width, height, "png"
            )
            if thumbnail is None:
                return self.return_not_found()
            return self.return_image(thumbnail, "image/png")

        @self.blueprint.route(
            "/<uuid:image_uid>/<int:dzi_level>" + "/<int:x>_<int:y>.<extension>",
            methods=["GET"],
        )
        @self.blueprint.route(
            "/<uuid:image_uid>/<int:dzi_level>"
            + "/<int:x>_<int:y>_<int:z>.<extension>",
            methods=["GET"],
        )
        def get_tile(
            image_uid: UUID,
            dzi_level: int,
            x: int,
            y: int,
            extension: str,
            z: Optional[int] = None,
        ) -> Response:
            tile = self._image_service.get_tile(
                image_uid, dzi_level, x, y, extension, z
            )
            return send_file(io.BytesIO(tile), mimetype="image/jpeg")

        @self.blueprint.route(
            "/<uuid:image_uid>",
            methods=["GET"],
        )
        def get_dzi(
            image_uid: UUID,
        ) -> Response:
            dzi = self._image_service.get_dzi(
                image_uid, url_for(".get_dzi", image_uid=image_uid) + "/"
            )
            return self.return_json(dzi.model_dump(mode="json", by_alias=True))
