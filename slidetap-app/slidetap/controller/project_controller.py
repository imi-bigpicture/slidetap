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

"""Controller for handling projects and items in projects."""
from uuid import UUID

from flask import Blueprint, current_app, request
from flask.wrappers import Response

from slidetap.controller.controller import SecuredController
from slidetap.serialization import (
    ProjectModel,
    ProjectSimplifiedModel,
)
from slidetap.services import LoginService, ProjectService


class ProjectController(SecuredController):
    """Controller for projects."""

    def __init__(
        self,
        login_service: LoginService,
        project_service: ProjectService,
    ):
        super().__init__(login_service, Blueprint("project", __name__))

        @self.blueprint.route("/create", methods=["Post"])
        def create_project() -> Response:
            """Create a project based on parameters in form.

            Returns
            ----------
            Response
                Response with created project's id.
            """

            project_data = ProjectModel(only=["name"]).load(request.get_json())
            assert isinstance(project_data, dict)
            session = login_service.get_current_session()
            try:
                project = project_service.create(session, project_data["name"])
                current_app.logger.debug(f"Created project {project.uid, project.name}")
                return self.return_json(ProjectModel().dump(project))
            except ValueError:
                current_app.logger.error(
                    "Failed to parse file due to error", exc_info=True
                )
                return self.return_bad_request()

        @self.blueprint.route("", methods=["GET"])
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
            project = ProjectModel().load(request.get_json())
            assert isinstance(project, dict)
            try:
                project = project_service.update(
                    project_uid, project["name"], project["attributes"]
                )
                if project is None:
                    return self.return_not_found()
                current_app.logger.debug(f"Updated project {project.uid, project.name}")
                return self.return_json(ProjectModel().dump(project))
            except ValueError:
                current_app.logger.error(
                    "Failed to parse file due to error", exc_info=True
                )
                return self.return_bad_request()

        @self.blueprint.route("/<uuid:project_uid>/uploadFile", methods=["POST"])
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
            except ValueError:
                current_app.logger.error(
                    "Failed to parse file due to error", exc_info=True
                )
                return self.return_bad_request()
            return self.return_json(ProjectModel().dump(project))

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

        @self.blueprint.route("/<uuid:project_uid>/pre_process", methods=["POST"])
        def pre_process(project_uid: UUID) -> Response:
            """Preprocess images for project specified by id.

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
            project = project_service.pre_process(project_uid, session)
            if project is None:
                return self.return_not_found()
            return self.return_json(ProjectModel().dump(project))

        @self.blueprint.route("/<uuid:project_uid>/process", methods=["POST"])
        def process(project_uid: UUID) -> Response:
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
            project = project_service.process(project_uid, session)
            if project is None:
                return self.return_not_found()
            return self.return_json(ProjectModel().dump(project))

        @self.blueprint.route("/<uuid:project_uid>/export", methods=["POST"])
        def export(project_uid: UUID) -> Response:
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
            project = project_service.export(project_uid)
            if project is None:
                return self.return_not_found()
            return self.return_json(ProjectModel().dump(project))

        @self.blueprint.route("/<uuid:project_uid>", methods=["GET"])
        def get_project(project_uid: UUID) -> Response:
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

        @self.blueprint.route("/<uuid:project_uid>/status", methods=["GET"])
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
            return self.return_json(project.status.value)

        @self.blueprint.route("<uuid:project_uid>/delete", methods=["POST"])
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

        @self.blueprint.route("<uuid:project_uid>/validation", methods=["GET"])
        def get_project_validation(project_uid: UUID) -> Response:
            """Get validation of project specified by id.

            Parameters
            ----------
            project_uid: UUID
                Id of project to get validation of.

            Returns
            ----------
            Response
                OK if successful.
            """
            is_valid = project_service.validate(project_uid)
            return self.return_json({"is_valid": is_valid})
