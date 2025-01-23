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

from slidetap.serialization import ProjectModel
from slidetap.serialization.validation import ProjectValidationModel
from slidetap.services.login.login_service import LoginService
from slidetap.services.project_service import ProjectService
from slidetap.services.validation_service import ValidationService
from slidetap.web.controller.controller import SecuredController
from slidetap.web.processing_service import ProcessingService


class ProjectController(SecuredController):
    """Controller for projects."""

    def __init__(
        self,
        login_service: LoginService,
        project_service: ProjectService,
        validation_service: ValidationService,
        processing_service: ProcessingService,
    ):
        super().__init__(login_service, Blueprint("project", __name__))
        self._model = ProjectModel()

        @self.blueprint.route("/create", methods=["Post"])
        def create_project() -> Response:
            """Create a project based on parameters in form.

            Returns
            ----------
            Response
                Response with created project's id.
            """
            project_name = "New project"
            session = login_service.get_current_session()
            try:
                project = processing_service.create_project(session, project_name)
                current_app.logger.debug(f"Created project {project.uid, project.name}")
                return self.return_json(self._model.dump(project))
            except Exception:
                current_app.logger.error(
                    "Failed to parse create project due to error", exc_info=True
                )
                return self.return_bad_request()

        @self.blueprint.route("", methods=["GET"])
        def get_projects() -> Response:
            """Get status of registered projects.

            Returns
            ----------
            Response
                Json-response of registered projects
            """
            return self.return_json(
                [
                    self._model.dump(project)
                    for project in project_service.get_all_of_root_schema()
                ]
            )

        @self.blueprint.route("/<uuid:project_uid>", methods=["Post"])
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
            project = self._model.load(request.get_json())
            try:
                project = project_service.update(project)
                if project is None:
                    return self.return_not_found()
                current_app.logger.debug(f"Updated project {project.uid, project.name}")
                return self.return_json(self._model.dump(project))
            except ValueError:
                current_app.logger.error(
                    "Failed to parse file due to error", exc_info=True
                )
                return self.return_bad_request()

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
            project = processing_service.export_project(project_uid)
            if project is None:
                return self.return_not_found()
            return self.return_json(self._model.dump(project))

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
            project = project_service.get_optional(project_uid)
            if project is None:
                return self.return_not_found()
            return self.return_json(self._model.dump(project))

        @self.blueprint.route("<uuid:project_uid>", methods=["DELETE"])
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
            deleted = project_service.delete(project_uid)
            if deleted is None:
                return self.return_not_found()
            if not deleted:
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
            validation = validation_service.get_validation_for_project(project_uid)
            current_app.logger.debug(
                f"Validation of project {project_uid}: {validation}"
            )
            return self.return_json(ProjectValidationModel().dump(validation))
