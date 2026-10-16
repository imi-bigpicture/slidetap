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

from http import HTTPStatus
from uuid import uuid4

import pytest
from decoy import Decoy
from decoy.matchers import Anything
from dishka import Provider, Scope, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.testclient import TestClient

from slidetap.model import CodeAttribute, Mapper, MappingItem
from slidetap.model.mapper import (
    MapperCreate,
    MapperGroup,
    MapperGroupCreate,
    MappingItemCreate,
    UnmappedValue,
    UnmappedValueKey,
    UnmappedValueRemap,
)
from slidetap.services import MapperService
from slidetap.web.routers import mapper_router
from slidetap.web.services import LoginService


@pytest.fixture()
def mapper_service(decoy: Decoy):
    return decoy.mock(cls=MapperService)


@pytest.fixture()
def test_client(decoy: Decoy, simple_app: FastAPI, mapper_service: MapperService):
    login_service = decoy.mock(cls=LoginService)
    service_provider = Provider(scope=Scope.APP)
    service_provider.provide(lambda: login_service, provides=LoginService)
    service_provider.provide(lambda: mapper_service, provides=MapperService)
    container = make_async_container(service_provider)
    simple_app.include_router(mapper_router)
    setup_dishka(container, simple_app)
    with TestClient(simple_app) as client:
        yield client


@pytest.fixture()
def mapper() -> Mapper:
    return Mapper(
        uid=uuid4(),
        name="mapper",
        attribute_schema_uid=uuid4(),
        root_attribute_schema_uid=uuid4(),
    )


@pytest.fixture()
def mapper_group(mapper: Mapper) -> MapperGroup:
    return MapperGroup(
        uid=uuid4(), name="group", mappers=[mapper.uid], default_enabled=True
    )


@pytest.mark.unittest
class TestSlideTapMapperRouter:
    @pytest.mark.parametrize(
        ("expression", "reason"),
        [("(unclosed", "not a valid regular expression"), ("(a+)+$", "exponential")],
    )
    def test_creating_a_mapping_with_an_unsafe_expression_is_refused(
        self,
        decoy: Decoy,
        test_client: TestClient,
        mapper_service: MapperService,
        code_attribute: CodeAttribute,
        expression: str,
        reason: str,
    ):
        # Arrange
        mapping = MappingItemCreate(
            mapper_uid=uuid4(), expression=expression, attribute=code_attribute
        )

        # Act
        response = test_client.post(
            "api/mappers/mappings/create",
            json=mapping.model_dump(mode="json", by_alias=True),
        )

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert reason in response.json()["detail"]
        decoy.verify(mapper_service.create_mapping(Anything()), times=0)

    def test_updating_a_mapping_with_an_unsafe_expression_is_refused(
        self,
        decoy: Decoy,
        test_client: TestClient,
        mapper_service: MapperService,
        code_attribute: CodeAttribute,
    ):
        # Arrange
        mapping = MappingItem(
            uid=uuid4(),
            mapper_uid=uuid4(),
            expression="(unclosed",
            attribute=code_attribute,
        )

        # Act
        response = test_client.post(
            f"api/mappers/mappings/mapping/{mapping.uid}",
            json=mapping.model_dump(mode="json", by_alias=True),
        )

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert "not a valid regular expression" in response.json()["detail"]
        decoy.verify(mapper_service.update_mapping(Anything()), times=0)

    def test_creating_a_mapping_with_a_safe_expression_is_saved(
        self,
        decoy: Decoy,
        test_client: TestClient,
        mapper_service: MapperService,
        code_attribute: CodeAttribute,
    ):
        # Arrange
        mapping = MappingItemCreate(
            mapper_uid=uuid4(), expression="Hematoxylin.*", attribute=code_attribute
        )
        created = MappingItem(
            uid=uuid4(),
            mapper_uid=mapping.mapper_uid,
            expression=mapping.expression,
            attribute=code_attribute,
        )
        decoy.when(mapper_service.create_mapping(Anything())).then_return(created)

        # Act
        response = test_client.post(
            "api/mappers/mappings/create",
            json=mapping.model_dump(mode="json", by_alias=True),
        )

        # Assert
        assert response.status_code == HTTPStatus.OK

    def test_a_mapper_is_created(
        self,
        decoy: Decoy,
        test_client: TestClient,
        mapper_service: MapperService,
        mapper: Mapper,
    ):
        # Arrange
        mapper_create = MapperCreate(
            name=mapper.name, attribute_schema_uid=mapper.attribute_schema_uid
        )
        decoy.when(mapper_service.create_mapper(mapper_create)).then_return(mapper)

        # Act
        response = test_client.post(
            "api/mappers/create",
            json=mapper_create.model_dump(mode="json", by_alias=True),
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json() == mapper.model_dump(mode="json", by_alias=True)

    def test_every_mapper_is_listed(
        self,
        decoy: Decoy,
        test_client: TestClient,
        mapper_service: MapperService,
        mapper: Mapper,
    ):
        # Arrange
        decoy.when(mapper_service.get_mappers()).then_return([mapper])

        # Act
        response = test_client.get("api/mappers")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert [listed["uid"] for listed in response.json()] == [str(mapper.uid)]

    def test_a_mapper_is_got(
        self,
        decoy: Decoy,
        test_client: TestClient,
        mapper_service: MapperService,
        mapper: Mapper,
    ):
        # Arrange
        decoy.when(mapper_service.get_mapper(mapper.uid)).then_return(mapper)

        # Act
        response = test_client.get(f"api/mappers/mapper/{mapper.uid}")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json()["uid"] == str(mapper.uid)

    def test_a_mapper_that_is_not_there_is_not_found(
        self, decoy: Decoy, test_client: TestClient, mapper_service: MapperService
    ):
        # Arrange
        mapper_uid = uuid4()
        decoy.when(mapper_service.get_mapper(mapper_uid)).then_return(None)

        # Act
        response = test_client.get(f"api/mappers/mapper/{mapper_uid}")

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND

    @pytest.mark.parametrize(
        ("deleted", "status_code"),
        [(True, HTTPStatus.OK), (False, HTTPStatus.NOT_FOUND)],
    )
    def test_delete_mapper_answers_whether_it_was_there(
        self,
        decoy: Decoy,
        test_client: TestClient,
        mapper_service: MapperService,
        deleted: bool,
        status_code: HTTPStatus,
    ):
        # Arrange
        mapper_uid = uuid4()
        decoy.when(mapper_service.delete_mapper(mapper_uid)).then_return(deleted)

        # Act
        response = test_client.delete(f"api/mappers/mapper/{mapper_uid}")

        # Assert
        assert response.status_code == status_code

    def test_the_mappings_of_a_mapper_are_got(
        self,
        decoy: Decoy,
        test_client: TestClient,
        mapper_service: MapperService,
        mapper: Mapper,
        code_attribute: CodeAttribute,
    ):
        # Arrange
        mapping = MappingItem(
            uid=uuid4(),
            mapper_uid=mapper.uid,
            expression="expression",
            attribute=code_attribute,
        )
        decoy.when(mapper_service.get_mappings_for_mapper(mapper.uid)).then_return(
            [mapping]
        )

        # Act
        response = test_client.get(f"api/mappers/mapper/{mapper.uid}/mapping")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert [listed["uid"] for listed in response.json()] == [str(mapping.uid)]

    def test_the_unmapped_values_of_a_project_are_got_for_a_batch(
        self,
        decoy: Decoy,
        test_client: TestClient,
        mapper_service: MapperService,
        mapper: Mapper,
    ):
        # Arrange
        project_uid = uuid4()
        batch_uid = uuid4()
        unmapped_value = UnmappedValue(
            attribute_schema_uid=mapper.attribute_schema_uid,
            display_name="Stain",
            value="hematoxylin",
            items=3,
            mapper_uid=mapper.uid,
        )
        decoy.when(
            mapper_service.get_unmapped_values(project_uid, batch_uid)
        ).then_return([unmapped_value])

        # Act
        response = test_client.get(
            f"api/mappers/project/{project_uid}/unmapped",
            params={"batch_uid": str(batch_uid)},
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json() == [
            unmapped_value.model_dump(mode="json", by_alias=True)
        ]

    def test_an_unmapped_value_is_remapped(
        self,
        decoy: Decoy,
        test_client: TestClient,
        mapper_service: MapperService,
    ):
        # Arrange
        project_uid = uuid4()
        key = UnmappedValueKey(attribute_schema_uid=uuid4(), value="hematoxylin")
        remap = UnmappedValueRemap(remapped_items=2, skipped_items=1)
        decoy.when(
            mapper_service.remap_unmapped_value(
                project_uid, key.attribute_schema_uid, key.value, None
            )
        ).then_return(remap)

        # Act
        response = test_client.post(
            f"api/mappers/project/{project_uid}/unmapped/remap",
            json=key.model_dump(mode="json", by_alias=True),
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json() == remap.model_dump(mode="json", by_alias=True)

    def test_a_mapper_group_is_created(
        self,
        decoy: Decoy,
        test_client: TestClient,
        mapper_service: MapperService,
        mapper_group: MapperGroup,
    ):
        # Arrange
        group_create = MapperGroupCreate(name=mapper_group.name, default_enabled=True)
        decoy.when(
            mapper_service.get_or_create_mapper_group(mapper_group.name, True)
        ).then_return(mapper_group)

        # Act
        response = test_client.post(
            "api/mappers/groups/create",
            json=group_create.model_dump(mode="json", by_alias=True),
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json()["uid"] == str(mapper_group.uid)

    def test_every_mapper_group_is_listed(
        self,
        decoy: Decoy,
        test_client: TestClient,
        mapper_service: MapperService,
        mapper_group: MapperGroup,
    ):
        # Arrange
        decoy.when(mapper_service.get_all_mapper_groups()).then_return([mapper_group])

        # Act
        response = test_client.get("api/mappers/groups")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert [listed["uid"] for listed in response.json()] == [str(mapper_group.uid)]

    def test_the_mappers_in_a_group_are_set(
        self,
        decoy: Decoy,
        test_client: TestClient,
        mapper_service: MapperService,
        mapper_group: MapperGroup,
    ):
        # Arrange
        decoy.when(
            mapper_service.set_mappers_in_group(mapper_group.uid, mapper_group.mappers)
        ).then_return(mapper_group)

        # Act
        response = test_client.post(
            f"api/mappers/groups/{mapper_group.uid}/mappers",
            json=[str(mapper_uid) for mapper_uid in mapper_group.mappers],
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json()["mappers"] == [
            str(mapper_uid) for mapper_uid in mapper_group.mappers
        ]

    def test_setting_the_mappers_of_a_group_that_is_not_there_is_not_found(
        self,
        decoy: Decoy,
        test_client: TestClient,
        mapper_service: MapperService,
    ):
        # Arrange
        group_uid = uuid4()
        decoy.when(mapper_service.set_mappers_in_group(group_uid, [])).then_return(None)

        # Act
        response = test_client.post(f"api/mappers/groups/{group_uid}/mappers", json=[])

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_a_mapping_is_got(
        self,
        decoy: Decoy,
        test_client: TestClient,
        mapper_service: MapperService,
        code_attribute: CodeAttribute,
    ):
        # Arrange
        mapping = MappingItem(
            uid=uuid4(),
            mapper_uid=uuid4(),
            expression="expression",
            attribute=code_attribute,
        )
        decoy.when(mapper_service.get_mapping(mapping.uid)).then_return(mapping)

        # Act
        response = test_client.get(f"api/mappers/mappings/mapping/{mapping.uid}")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json()["uid"] == str(mapping.uid)

    def test_a_mapping_that_is_not_there_is_not_found(
        self, decoy: Decoy, test_client: TestClient, mapper_service: MapperService
    ):
        # Arrange
        mapping_uid = uuid4()
        decoy.when(mapper_service.get_mapping(mapping_uid)).then_return(None)

        # Act
        response = test_client.get(f"api/mappers/mappings/mapping/{mapping_uid}")

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_a_mapping_is_deleted(
        self, decoy: Decoy, test_client: TestClient, mapper_service: MapperService
    ):
        # Arrange
        mapping_uid = uuid4()
        decoy.when(mapper_service.delete_mapping(mapping_uid)).then_return(True)

        # Act
        response = test_client.delete(f"api/mappers/mappings/mapping/{mapping_uid}")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"status": "ok"}

    def test_deleting_a_mapping_that_is_not_there_is_not_found(
        self, decoy: Decoy, test_client: TestClient, mapper_service: MapperService
    ):
        # Arrange
        mapping_uid = uuid4()
        decoy.when(mapper_service.delete_mapping(mapping_uid)).then_return(False)

        # Act
        response = test_client.delete(f"api/mappers/mappings/mapping/{mapping_uid}")

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_deleting_a_mapping_the_service_refuses_is_a_bad_request(
        self, decoy: Decoy, test_client: TestClient, mapper_service: MapperService
    ):
        # Arrange
        mapping_uid = uuid4()
        decoy.when(mapper_service.delete_mapping(mapping_uid)).then_raise(
            ValueError("Mapping is in use")
        )

        # Act
        response = test_client.delete(f"api/mappers/mappings/mapping/{mapping_uid}")

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json()["detail"] == "Failed to delete mapping"
