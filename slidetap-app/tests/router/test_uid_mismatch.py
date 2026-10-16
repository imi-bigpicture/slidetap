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

"""An update names what it changes twice, in the path and in the body, and is
refused where the two differ."""

from collections.abc import Callable
from http import HTTPStatus
from typing import Any
from uuid import uuid4

import pytest
from decoy import Decoy
from decoy.matchers import Anything
from dishka import Provider, Scope, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slidetap_example import ExampleSchema

from slidetap.model import Batch, CodeAttribute, Dataset, Mapper, MappingItem
from slidetap.model.item import Sample
from slidetap.services import (
    AttributeService,
    DatasetService,
    ItemService,
    MapperService,
)
from slidetap.task import Scheduler
from slidetap.web.routers import (
    attribute_router,
    dataset_router,
    item_router,
    mapper_router,
)
from slidetap.web.services import (
    ImagePipelineService,
    LoginService,
    MetadataExportService,
)


def _returning(service: Any) -> Callable[[], Any]:
    """A factory for the container that gives the service it is made with."""
    return lambda: service


@pytest.fixture()
def item_service(decoy: Decoy):
    return decoy.mock(cls=ItemService)


@pytest.fixture()
def mapper_service(decoy: Decoy):
    return decoy.mock(cls=MapperService)


@pytest.fixture()
def dataset_service(decoy: Decoy):
    return decoy.mock(cls=DatasetService)


@pytest.fixture()
def attribute_service(decoy: Decoy):
    return decoy.mock(cls=AttributeService)


@pytest.fixture()
def test_client(
    decoy: Decoy,
    simple_app: FastAPI,
    item_service: ItemService,
    mapper_service: MapperService,
    dataset_service: DatasetService,
    attribute_service: AttributeService,
):
    service_provider = Provider(scope=Scope.APP)
    mocked_services = {
        LoginService: decoy.mock(cls=LoginService),
        ItemService: item_service,
        MapperService: mapper_service,
        DatasetService: dataset_service,
        AttributeService: attribute_service,
        Scheduler: decoy.mock(cls=Scheduler),
        ImagePipelineService: decoy.mock(cls=ImagePipelineService),
        MetadataExportService: decoy.mock(cls=MetadataExportService),
    }
    for service_type, service in mocked_services.items():
        service_provider.provide(_returning(service), provides=service_type)
    container = make_async_container(service_provider)
    simple_app.include_router(item_router)
    simple_app.include_router(mapper_router)
    simple_app.include_router(dataset_router)
    simple_app.include_router(attribute_router)
    setup_dishka(container, simple_app)
    with TestClient(simple_app) as client:
        yield client


@pytest.fixture()
def sample(schema: ExampleSchema, dataset: Dataset, batch: Batch) -> Sample:
    return Sample(
        uid=uuid4(),
        identifier="patient 1",
        dataset_uid=dataset.uid,
        batch_uid=batch.uid,
        schema_uid=schema.patient_schema_uid,
    )


@pytest.fixture()
def mapper() -> Mapper:
    return Mapper(
        uid=uuid4(),
        name="mapper",
        attribute_schema_uid=uuid4(),
        root_attribute_schema_uid=uuid4(),
    )


@pytest.fixture()
def mapping(mapper: Mapper, code_attribute: CodeAttribute) -> MappingItem:
    return MappingItem(
        uid=uuid4(),
        mapper_uid=mapper.uid,
        expression="expression",
        attribute=code_attribute,
    )


@pytest.mark.unittest
class TestUidMismatch:
    def test_save_item_with_a_body_for_another_item_is_refused(
        self,
        decoy: Decoy,
        test_client: TestClient,
        item_service: ItemService,
        sample: Sample,
    ):
        # Act
        response = test_client.post(
            f"api/items/item/{uuid4()}",
            json=sample.model_dump(mode="json", by_alias=True),
        )

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST
        decoy.verify(item_service.update(Anything()), times=0)

    def test_save_item_with_a_body_for_the_item_is_saved(
        self,
        decoy: Decoy,
        test_client: TestClient,
        item_service: ItemService,
        sample: Sample,
    ):
        # Arrange
        decoy.when(item_service.update(Anything())).then_return(sample)

        # Act
        response = test_client.post(
            f"api/items/item/{sample.uid}",
            json=sample.model_dump(mode="json", by_alias=True),
        )

        # Assert
        assert response.status_code == HTTPStatus.OK

    def test_update_mapper_with_a_body_for_another_mapper_is_refused(
        self,
        decoy: Decoy,
        test_client: TestClient,
        mapper_service: MapperService,
        mapper: Mapper,
    ):
        # Act
        response = test_client.post(
            f"api/mappers/mapper/{uuid4()}",
            json=mapper.model_dump(mode="json", by_alias=True),
        )

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST
        decoy.verify(mapper_service.update_mapper(Anything()), times=0)

    def test_update_mapper_with_a_body_for_the_mapper_is_saved(
        self,
        decoy: Decoy,
        test_client: TestClient,
        mapper_service: MapperService,
        mapper: Mapper,
    ):
        # Arrange
        decoy.when(mapper_service.update_mapper(Anything())).then_return(mapper)

        # Act
        response = test_client.post(
            f"api/mappers/mapper/{mapper.uid}",
            json=mapper.model_dump(mode="json", by_alias=True),
        )

        # Assert
        assert response.status_code == HTTPStatus.OK

    def test_update_mapping_with_a_body_for_another_mapping_is_refused(
        self,
        decoy: Decoy,
        test_client: TestClient,
        mapper_service: MapperService,
        mapping: MappingItem,
    ):
        # Act
        response = test_client.post(
            f"api/mappers/mappings/mapping/{uuid4()}",
            json=mapping.model_dump(mode="json", by_alias=True),
        )

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST
        decoy.verify(mapper_service.update_mapping(Anything()), times=0)

    def test_update_mapping_with_a_body_for_the_mapping_is_saved(
        self,
        decoy: Decoy,
        test_client: TestClient,
        mapper_service: MapperService,
        mapping: MappingItem,
    ):
        # Arrange
        decoy.when(mapper_service.update_mapping(Anything())).then_return(mapping)

        # Act
        response = test_client.post(
            f"api/mappers/mappings/mapping/{mapping.uid}",
            json=mapping.model_dump(mode="json", by_alias=True),
        )

        # Assert
        assert response.status_code == HTTPStatus.OK

    def test_update_attribute_with_a_body_for_another_attribute_is_refused(
        self,
        decoy: Decoy,
        test_client: TestClient,
        attribute_service: AttributeService,
        code_attribute: CodeAttribute,
    ):
        # Act
        response = test_client.post(
            f"api/attributes/attribute/{uuid4()}",
            json=code_attribute.model_dump(mode="json", by_alias=True),
        )

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST
        decoy.verify(attribute_service.update(Anything()), times=0)

    def test_update_attribute_answers_with_the_attribute_as_stored(
        self,
        decoy: Decoy,
        test_client: TestClient,
        attribute_service: AttributeService,
        code_attribute: CodeAttribute,
    ):
        """What is stored can differ from what was sent, such as a display value
        the service works out."""
        # Arrange
        stored = code_attribute.model_copy(update={"display_value": "as stored"})
        decoy.when(attribute_service.update(Anything())).then_return(stored)

        # Act
        response = test_client.post(
            f"api/attributes/attribute/{code_attribute.uid}",
            json=code_attribute.model_dump(mode="json", by_alias=True),
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json()["displayValue"] == "as stored"

    def test_update_dataset_with_a_body_for_another_dataset_is_refused(
        self,
        decoy: Decoy,
        test_client: TestClient,
        dataset_service: DatasetService,
        dataset: Dataset,
    ):
        # Act
        response = test_client.post(
            f"api/datasets/dataset/{uuid4()}",
            json=dataset.model_dump(mode="json", by_alias=True),
        )

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST
        decoy.verify(dataset_service.update(Anything()), times=0)
