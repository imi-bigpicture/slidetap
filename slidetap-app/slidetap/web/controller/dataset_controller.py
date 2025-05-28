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

"""Controller for handling completed datasets."""
from uuid import UUID

from flask import Blueprint
from flask.wrappers import Response

from slidetap.serialization.dataset import DatasetModel
from slidetap.services import DatasetService, ProjectService
from slidetap.web.controller.controller import SecuredController
from slidetap.web.services import LoginService


class DatasetController(SecuredController):
    """Controller for datasets."""

    def __init__(
        self,
        login_service: LoginService,
        project_service: ProjectService,
        dataset_service: DatasetService,
    ):
        super().__init__(login_service, Blueprint("dataset", __name__))

        @self.blueprint.route("/importable", methods=["Get"])
        def importable_datasets() -> Response:
            """Get status of registered projects.

            Returns
            ----------
            Response
                Json-response of registered projects
            """
            # datasets = dataset_service.get_importable_datasets()
            # datasets = []
            # model = DatasetModel()
            # return self.return_json([model.dump(dataset) for dataset in datasets])
            return self.return_bad_request()

        @self.blueprint.route("/import", methods=["Post"])
        def import_dataset() -> Response:
            """Create a project based on parameters in form.

            Returns
            ----------
            Response
                Response with created project's id.
            """
            # model = DatasetModel()
            # dataset_data = model.load(request.get_json())
            # assert isinstance(dataset_data, dict)
            # try:

            #     dataset = Dataset(**dataset_data)
            #     current_app.logger.info(
            #         f"Importing dataset {dataset.uid, dataset.name, dataset.path}"
            #     )
            #     dataset_service.import_dataset(dataset)
            #     return self.return_json(model.dump(dataset))
            # except ValueError:
            #     current_app.logger.error(
            #         "Failed to parse file due to error", exc_info=True
            #     )
            #     return self.return_bad_request()
            return self.return_bad_request()

        @self.blueprint.route("", methods=["GET"])
        def get_datasets() -> Response:
            """Get status of registered projects.

            Returns
            ----------
            Response
                Json-response of registered projects
            """
            # projects = ProjectSimplifiedModel().dump(
            #     project_service.get_all(ProjectStatus.EXPORT_COMPLETE), many=True
            # )
            # datasets = []
            # return self.return_json(datasets)
            return self.return_bad_request()

        @self.blueprint.route("<uuid:dataset_uid>", methods=["DELETE"])
        def delete_dataset(dataset_uid: UUID) -> Response:
            """Delete project specified by id.

            Parameters
            ----------
            dataset_uid: UUID
                Id of project.

            Returns
            ----------
            Response
                Ok if successful.
            """
            # project = project_service.delete(dataset_uid)
            # if project is None:
            #     return self.return_not_found()
            # if not project.deleted:
            #     return self.return_bad_request()
            # return self.return_ok()
            return self.return_bad_request()

        @self.blueprint.route("<uuid:dataset_uid>", methods=["GET"])
        def get_dataset(dataset_uid: UUID) -> Response:
            """Get status of project specified by id.

            Parameters
            ----------
            dataset_uid: UUID
                Id of project.

            Returns
            ----------
            Response
                Json-response of project.
            """
            dataset = dataset_service.get(dataset_uid)
            if dataset is None:
                return self.return_not_found()
            return self.return_json(DatasetModel().dump(dataset))
