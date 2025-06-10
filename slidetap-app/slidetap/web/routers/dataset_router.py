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

"""FastAPI router for handling completed datasets."""
import logging
from http import HTTPStatus
from typing import List
from uuid import UUID

from fastapi import HTTPException

from slidetap.model import Dataset
from slidetap.services import DatasetService, ProjectService
from slidetap.web.routers.router import SecuredRouter


class DatasetRouter(SecuredRouter):
    """FastAPI router for datasets."""

    def __init__(
        self,
        project_service: ProjectService,
        dataset_service: DatasetService,
    ):
        self._project_service = project_service
        self._dataset_service = dataset_service
        self._logger = logging.getLogger(__name__)
        super().__init__()

        # Register routes
        self._register_routes()

    def _register_routes(self):
        """Register all dataset routes."""

        @self.router.get("/importable")
        async def importable_datasets(user=self.auth_dependency()) -> List[Dataset]:
            """Get importable datasets.

            Returns
            ----------
            List[Dataset]
                List of importable datasets
            """
            # This functionality is not implemented in the original controller
            # Keeping as placeholder that raises not implemented error
            raise HTTPException(
                status_code=HTTPStatus.NOT_IMPLEMENTED,
                detail="Importable datasets functionality not implemented",
            )

        @self.router.post("/import")
        async def import_dataset(
            dataset: Dataset, user=self.auth_dependency()
        ) -> Dataset:
            """Import a dataset.

            Parameters
            ----------
            dataset: Dataset
                Dataset to import

            Returns
            ----------
            Dataset
                Imported dataset
            """
            # This functionality is not implemented in the original controller
            # Keeping as placeholder that raises not implemented error
            raise HTTPException(
                status_code=HTTPStatus.NOT_IMPLEMENTED,
                detail="Dataset import functionality not implemented",
            )

        @self.router.get("")
        async def get_datasets(user=self.auth_dependency()) -> List[Dataset]:
            """Get all datasets.

            Returns
            ----------
            List[Dataset]
                List of all datasets
            """
            # This functionality is not implemented in the original controller
            # Keeping as placeholder that raises not implemented error
            raise HTTPException(
                status_code=HTTPStatus.NOT_IMPLEMENTED,
                detail="Get datasets functionality not implemented",
            )

        @self.router.delete("/dataset/{dataset_uid}")
        async def delete_dataset(
            dataset_uid: UUID, user=self.auth_dependency()
        ) -> dict:
            """Delete dataset specified by id.

            Parameters
            ----------
            dataset_uid: UUID
                Id of dataset to delete.

            Returns
            ----------
            dict
                Success message if successful.
            """
            # This functionality is not implemented in the original controller
            # Keeping as placeholder that raises not implemented error
            raise HTTPException(
                status_code=HTTPStatus.NOT_IMPLEMENTED,
                detail="Dataset deletion functionality not implemented",
            )

        @self.router.get("/dataset/{dataset_uid}")
        async def get_dataset(
            dataset_uid: UUID, user=self.auth_dependency()
        ) -> Dataset:
            """Get dataset specified by id.

            Parameters
            ----------
            dataset_uid: UUID
                Id of dataset.

            Returns
            ----------
            Dataset
                Dataset data.
            """
            dataset = self._dataset_service.get(dataset_uid)
            if dataset is None:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail=f"Dataset with id {dataset_uid} not found",
                )
            return dataset
