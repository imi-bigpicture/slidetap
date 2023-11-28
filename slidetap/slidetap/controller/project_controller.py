"""Controller for handling projects and items in projects."""
from uuid import UUID

from flask import Blueprint, current_app, request
from flask.wrappers import Response

from slidetap.controller.controller import Controller
from slidetap.serialization import (
    ItemModelFactory,
    ProjectModel,
    ProjectSimplifiedModel,
)
from slidetap.services import LoginService, ProjectService


class ProjectController(Controller):
    """Controller for projects."""

    def __init__(
        self,
        login_service: LoginService,
        project_service: ProjectService,
    ):
        super().__init__(login_service, Blueprint("project", __name__))

        @self.blueprint.route("/create", methods=["Post"])
        @self.login_service.validate_auth()
        def create_project() -> Response:
            """Create a project based on parameters in form.

            Returns
            ----------
            Response
                Response with created project's id.
            """

            project_data = ProjectModel(only=["name"]).load(request.get_json())
            assert isinstance(project_data, dict)
            try:
                project = project_service.create(project_data["name"])
                current_app.logger.debug(f"Created project {project.uid, project.name}")
                return self.return_json(ProjectModel().dump(project))
            except ValueError as error:
                current_app.logger.error(
                    f"Failed to parse file due to error {error}", error
                )
                return self.return_bad_request()

        @self.blueprint.route("", methods=["GET"])
        @self.login_service.validate_auth()
        def status_projects() -> Response:
            """Get status of registered projects.

            Returns
            ----------
            Response
                Json-response of registered projects
            """
            projects = ProjectSimplifiedModel().dump(
                project_service.get_all(), many=True
            )
            return self.return_json(projects)

        @self.blueprint.route("/<uuid:project_uid>/update", methods=["Post"])
        @self.login_service.validate_auth()
        def update_project(project_uid: UUID) -> Response:
            """Update project specified by id with data from form.

            Parameters
            ----------
            project_uid: UUID
                Id of project to update

            Returns
            ----------
            Response
                OK response if successful.
            """
            if "name" not in request.form:
                return self.return_bad_request()
            project_name = request.form["name"]
            try:
                project = project_service.update(project_uid, project_name)
                if project is None:
                    return self.return_not_found()
                current_app.logger.debug(f"Updated project {project.uid, project.name}")
                return self.return_ok()
            except ValueError as error:
                current_app.logger.error(f"Failed to parse file due to error {error}")
                return self.return_bad_request()

        @self.blueprint.route("/<uuid:project_uid>/uploadFile", methods=["POST"])
        @self.login_service.validate_auth()
        def upload_project_file(project_uid: UUID) -> Response:
            """Search for metadata and images for project specified by id
            using search criteria specified in posted file.

            Parameters
            ----------
            project_uid: UUID
                Id of project to search.

            Returns
            ----------
            Response
                OK response if successful.
            """
            if "file" not in request.files:
                current_app.logger.error("No file in request.")
                return self.return_bad_request()
            file = request.files["file"]
            session = login_service.get_current_session()
            try:
                project = project_service.upload(project_uid, session, file)
                if project is None:
                    current_app.logger.error(
                        f"No project found with uid {project_uid}."
                    )
                    return self.return_not_found()
            except ValueError as error:
                current_app.logger.error(f"Failed to parse file due to error {error}")
                return self.return_bad_request()
            return self.return_ok()

        @self.blueprint.route(
            "/<uuid:project_uid>/items/<uuid:item_schema_uid>/count", methods=["GET"]
        )
        def get_count(project_uid: UUID, item_schema_uid: UUID) -> Response:
            selected = request.args.get("selected", None)
            if selected is not None:
                selected = bool(selected)
            count = project_service.item_count(project_uid, item_schema_uid, selected)
            if count is None:
                return self.return_not_found()
            return self.return_json(count)

        @self.blueprint.route(
            "/<uuid:project_uid>/items/<uuid:item_schema_uid>",
        )
        def get_items(project_uid: UUID, item_schema_uid: UUID) -> Response:
            """Get items of specified type from project.

            Parameters
            ----------
            project_uid: UUID
                Id of project to get samples from.
            item_type_uid: UUID
                Item type to get.

            Request arguments
            ----------
            name: Optional[str] = None
                Optional item type name to get.
            selected: Optional[bool] = None
                Optional to only include selected (True) or non-selected
                (False) items.

            Returns
            ----------
            Response
                Json-response of items.
            """
            included = request.args.get("included", None)
            if included is not None:
                included = included == "true"
            else:
                included = True
            excluded = request.args.get("excluded", None)
            if excluded is not None:
                excluded = excluded == "true"
            else:
                excluded = False
            items = project_service.items(
                project_uid, item_schema_uid, included, excluded
            )
            if items is None:
                return self.return_not_found()
            if len(items) == 0:
                return self.return_json([])
            model = ItemModelFactory().create_simplified(items[0].schema)
            return self.return_json(model().dump(items, many=True))

        @self.blueprint.route("/<uuid:project_uid>/start", methods=["POST"])
        @self.login_service.validate_auth()
        def start(project_uid: UUID) -> Response:
            """Start project specified by id. Accepts selected items in
             project and start downloading images.

            Parameters
            ----------
            project_uid: UUID
                Id of project.

            Returns
            ----------
            Response
                OK if successful.
            """
            current_app.logger.info(f"Starting project {project_uid}.")
            session = login_service.get_current_session()
            project = project_service.start(project_uid, session)
            if project is None:
                return self.return_not_found()
            return self.return_ok()

        @self.blueprint.route("/<uuid:project_uid>/submit", methods=["POST"])
        @self.login_service.validate_auth()
        def submit(project_uid: UUID) -> Response:
            """Submit project specified by id to storage.

            Parameters
            ----------
            project_uid: UUID
                Id of project.

            Returns
            ----------
            Response
                OK if successful.
            """
            project = project_service.submit(project_uid)
            if project is None:
                return self.return_not_found()
            return self.return_ok()

        @self.blueprint.route("/<uuid:project_uid>/status", methods=["GET"])
        @self.login_service.validate_auth()
        def status_project(project_uid: UUID) -> Response:
            """Get status of project specified by id.

            Parameters
            ----------
            project_uid: UUID
                Id of project.

            Returns
            ----------
            Response
                Json-response of project.
            """
            project = project_service.get(project_uid)
            if project is None:
                return self.return_not_found()
            return self.return_json(ProjectModel().dump(project))

        @self.blueprint.route("<uuid:project_uid>/delete", methods=["POST"])
        @self.login_service.validate_auth()
        def delete_project(project_uid: UUID) -> Response:
            """Delete project specified by id.

            Parameters
            ----------
            project_uid: UUID
                Id of project.

            Returns
            ----------
            Response
                Ok if successful.
            """
            project = project_service.delete(project_uid)
            if project is None:
                return self.return_not_found()
            if not project.deleted:
                return self.return_bad_request()
            return self.return_ok()
