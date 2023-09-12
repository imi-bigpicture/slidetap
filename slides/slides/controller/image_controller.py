"""Controller for accessing image data."""
import io
from typing import Optional
from uuid import UUID

from flask import Blueprint, request, send_file
from flask.wrappers import Response

from slides.controller import Controller
from slides.serialization import DziModel, ImageSimplifiedModel
from slides.services import ImageService, LoginService
from slides.config import Config


class ImageController(Controller):
    def __init__(
        self,
        login_service: LoginService,
        image_service: ImageService,
        config: Config,
    ):
        super().__init__(login_service, Blueprint("image", __name__))
        self._image_service = image_service
        self._config = config

        @self.blueprint.route("/thumbnails/<uuid:project_uid>", methods=["GET"])
        def get_thumbnails(project_uid: UUID) -> Response:
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
            images = image_service.get_images_with_thumbnail(project_uid)
            if images is None:
                return self.return_not_found()
            return self.return_json(ImageSimplifiedModel().dump(images, many=True))

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
            thumbnail = self._image_service.get_thumbnail(image_uid, width, height)
            if thumbnail is None:
                return self.return_not_found()
            return self.return_bytes(thumbnail)

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
                image_uid, self._config.SLIDES_WEBAPPURL + f"/api/image/{image_uid}/"
            )
            return self.return_json(DziModel().dump(dzi))
