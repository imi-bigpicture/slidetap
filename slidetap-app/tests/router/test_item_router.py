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

import datetime
from http import HTTPStatus
from uuid import uuid4

import pytest
from decoy import Decoy
from decoy.matchers import Anything
from dishka import Provider, Scope, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slidetap_example import ExampleSchema

from slidetap.model import (
    Batch,
    Dataset,
    ItemNeighbours,
    MoveAttributeRequest,
    NewChildSuggestion,
    NotAllowedActionError,
    NotFoundError,
    ReviewIssue,
    ReviewIssueSource,
    ReviewRequest,
    ReviewStatus,
)
from slidetap.model.item import Sample
from slidetap.model.item_select import ItemBulkSelect, ItemSelect, ItemSelectResult
from slidetap.services import ItemService, MapperService, OverviewService, ReviewService
from slidetap.web import SlideTapWebAppFactory
from slidetap.web.routers import item_router
from slidetap.web.services import (
    ImagePipelineService,
    LoginService,
    MetadataExportService,
)


@pytest.fixture()
def image_pipeline_service(decoy: Decoy):
    return decoy.mock(cls=ImagePipelineService)


@pytest.fixture()
def item_service(decoy: Decoy):
    return decoy.mock(cls=ItemService)


@pytest.fixture()
def mapper_service(decoy: Decoy):
    return decoy.mock(cls=MapperService)


@pytest.fixture()
def review_service(decoy: Decoy):
    return decoy.mock(cls=ReviewService)


@pytest.fixture()
def overview_service(decoy: Decoy):
    return decoy.mock(cls=OverviewService)


@pytest.fixture()
def metadata_export_service(decoy: Decoy):
    return decoy.mock(cls=MetadataExportService)


@pytest.fixture()
def test_client(
    decoy: Decoy,
    simple_app: FastAPI,
    image_pipeline_service: ImagePipelineService,
    item_service: ItemService,
    mapper_service: MapperService,
    review_service: ReviewService,
    overview_service: OverviewService,
    metadata_export_service: MetadataExportService,
):
    login_service = decoy.mock(cls=LoginService)
    service_provider = Provider(scope=Scope.APP)
    service_provider.provide(lambda: login_service, provides=LoginService)
    service_provider.provide(lambda: item_service, provides=ItemService)
    service_provider.provide(lambda: mapper_service, provides=MapperService)
    service_provider.provide(lambda: review_service, provides=ReviewService)
    service_provider.provide(lambda: overview_service, provides=OverviewService)
    service_provider.provide(
        lambda: metadata_export_service, provides=MetadataExportService
    )
    service_provider.provide(
        lambda: image_pipeline_service, provides=ImagePipelineService
    )
    container = make_async_container(service_provider)
    simple_app.include_router(item_router)
    simple_app.add_exception_handler(NotFoundError, SlideTapWebAppFactory._not_found)
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
def review_issue(sample: Sample) -> ReviewIssue:
    return ReviewIssue(
        uid=uuid4(),
        item_uid=sample.uid,
        item_identifier=sample.identifier,
        item_schema_uid=sample.schema_uid,
        review_unit_uid=sample.uid,
        reason="Wrong stain",
        source=ReviewIssueSource.USER,
        raised_at=datetime.datetime(2026, 1, 1),
    )


@pytest.mark.unittest
class TestSlideTapItemRouter:
    @pytest.mark.parametrize(
        ("error", "status_code"),
        [
            (NotAllowedActionError("The project is view only"), HTTPStatus.CONFLICT),
            (NotFoundError("Image does not exist."), HTTPStatus.NOT_FOUND),
        ],
    )
    def test_a_retry_refused_for_one_image_retries_none(
        self,
        decoy: Decoy,
        test_client: TestClient,
        image_pipeline_service: ImagePipelineService,
        error: Exception,
        status_code: HTTPStatus,
    ):
        """Every image is checked before any is queued."""
        # Arrange
        image_uids = [uuid4(), uuid4()]
        decoy.when(image_pipeline_service.assert_can_retry(image_uids)).then_raise(
            error
        )

        # Act
        response = test_client.post(
            "api/items/retry", json=[str(image_uid) for image_uid in image_uids]
        )

        # Assert
        assert response.status_code == status_code
        decoy.verify(image_pipeline_service.retry(Anything()), times=0)

    def test_a_retry_of_images_that_can_be_retried_retries_each(
        self,
        decoy: Decoy,
        test_client: TestClient,
        image_pipeline_service: ImagePipelineService,
    ):
        # Arrange
        image_uids = [uuid4(), uuid4()]

        # Act
        response = test_client.post(
            "api/items/retry", json=[str(image_uid) for image_uid in image_uids]
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        for image_uid in image_uids:
            decoy.verify(image_pipeline_service.retry(image_uid), times=1)

    def test_an_item_is_got(
        self,
        decoy: Decoy,
        test_client: TestClient,
        item_service: ItemService,
        sample: Sample,
    ):
        # Arrange
        decoy.when(item_service.get_optional(sample.uid)).then_return(sample)

        # Act
        response = test_client.get(f"api/items/item/{sample.uid}")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json()["uid"] == str(sample.uid)
        assert response.json()["identifier"] == sample.identifier

    def test_an_item_that_is_not_there_is_not_found(
        self, decoy: Decoy, test_client: TestClient, item_service: ItemService
    ):
        # Arrange
        item_uid = uuid4()
        decoy.when(item_service.get_optional(item_uid)).then_return(None)

        # Act
        response = test_client.get(f"api/items/item/{item_uid}")

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND

    @pytest.mark.parametrize("preview", ["patient 1: male", None])
    def test_the_preview_of_an_item_is_got(
        self,
        decoy: Decoy,
        test_client: TestClient,
        metadata_export_service: MetadataExportService,
        preview: str | None,
    ):
        # Arrange
        item_uid = uuid4()
        decoy.when(metadata_export_service.preview_item(item_uid)).then_return(preview)

        # Act
        response = test_client.get(f"api/items/item/{item_uid}/preview")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"preview": preview}

    def test_the_review_status_of_an_item_is_set(
        self,
        decoy: Decoy,
        test_client: TestClient,
        review_service: ReviewService,
        sample: Sample,
    ):
        # Arrange
        request = ReviewRequest(status=ReviewStatus.FLAGGED, reason="Wrong stain")
        decoy.when(
            review_service.set_review_status(
                sample.uid, ReviewStatus.FLAGGED, "Wrong stain"
            )
        ).then_return(sample)

        # Act
        response = test_client.post(
            f"api/items/item/{sample.uid}/review",
            json=request.model_dump(mode="json", by_alias=True),
        )

        # Assert
        assert response.status_code == HTTPStatus.OK

    @pytest.mark.parametrize(
        ("outcome", "status_code"),
        [
            (NotAllowedActionError("Unit holds invalid items"), HTTPStatus.CONFLICT),
            (None, HTTPStatus.NOT_FOUND),
        ],
    )
    def test_a_review_status_that_cannot_be_set_is_refused(
        self,
        decoy: Decoy,
        test_client: TestClient,
        review_service: ReviewService,
        outcome: Exception | None,
        status_code: HTTPStatus,
    ):
        # Arrange
        item_uid = uuid4()
        stub = decoy.when(
            review_service.set_review_status(item_uid, ReviewStatus.REVIEWED, None)
        )
        if outcome is None:
            stub.then_return(None)
        else:
            stub.then_raise(outcome)

        # Act
        response = test_client.post(
            f"api/items/item/{item_uid}/review",
            json=ReviewRequest(status=ReviewStatus.REVIEWED).model_dump(
                mode="json", by_alias=True
            ),
        )

        # Assert
        assert response.status_code == status_code

    def test_an_issue_is_raised_on_an_item_by_a_user(
        self,
        decoy: Decoy,
        test_client: TestClient,
        review_service: ReviewService,
        review_issue: ReviewIssue,
    ):
        # Arrange
        decoy.when(
            review_service.raise_issue(
                review_issue.item_uid, review_issue.reason, ReviewIssueSource.USER
            )
        ).then_return(review_issue)

        # Act
        response = test_client.post(
            f"api/items/item/{review_issue.item_uid}/issues",
            json={"reason": review_issue.reason},
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json() == review_issue.model_dump(mode="json", by_alias=True)

    def test_an_issue_raised_on_an_item_under_no_review_unit_is_not_found(
        self, decoy: Decoy, test_client: TestClient, review_service: ReviewService
    ):
        # Arrange
        item_uid = uuid4()
        decoy.when(
            review_service.raise_issue(item_uid, "reason", ReviewIssueSource.USER)
        ).then_return(None)

        # Act
        response = test_client.post(
            f"api/items/item/{item_uid}/issues", json={"reason": "reason"}
        )

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_the_issues_of_an_item_are_got_with_the_resolved_when_asked(
        self,
        decoy: Decoy,
        test_client: TestClient,
        review_service: ReviewService,
        review_issue: ReviewIssue,
    ):
        # Arrange
        decoy.when(
            review_service.get_issues(review_issue.review_unit_uid, True)
        ).then_return([review_issue])

        # Act
        response = test_client.get(
            f"api/items/item/{review_issue.review_unit_uid}/issues",
            params={"includeResolved": "true"},
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert [issue["uid"] for issue in response.json()] == [str(review_issue.uid)]

    def test_an_issue_is_resolved(
        self,
        decoy: Decoy,
        test_client: TestClient,
        review_service: ReviewService,
        review_issue: ReviewIssue,
    ):
        # Arrange
        resolved = review_issue.model_copy(
            update={"resolved_at": datetime.datetime(2026, 1, 2)}
        )
        decoy.when(review_service.resolve_issue(review_issue.uid)).then_return(resolved)

        # Act
        response = test_client.post(f"api/items/issues/{review_issue.uid}/resolve")

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json()["resolvedAt"] is not None

    @pytest.mark.parametrize(
        ("outcome", "status_code"),
        [
            (NotAllowedActionError("Raised by validation"), HTTPStatus.CONFLICT),
            (None, HTTPStatus.NOT_FOUND),
        ],
    )
    def test_an_issue_that_cannot_be_resolved_is_refused(
        self,
        decoy: Decoy,
        test_client: TestClient,
        review_service: ReviewService,
        outcome: Exception | None,
        status_code: HTTPStatus,
    ):
        # Arrange
        issue_uid = uuid4()
        stub = decoy.when(review_service.resolve_issue(issue_uid))
        if outcome is None:
            stub.then_return(None)
        else:
            stub.then_raise(outcome)

        # Act
        response = test_client.post(f"api/items/issues/{issue_uid}/resolve")

        # Assert
        assert response.status_code == status_code

    def test_invalid_review_units_are_flagged_in_a_batch(
        self, decoy: Decoy, test_client: TestClient, review_service: ReviewService
    ):
        # Arrange
        dataset_uid = uuid4()
        batch_uid = uuid4()

        # Act
        response = test_client.post(
            "api/items/flag-invalid",
            params={"datasetUid": str(dataset_uid), "batchUid": str(batch_uid)},
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        decoy.verify(
            review_service.flag_invalid_review_units(dataset_uid, batch_uid), times=1
        )

    def test_an_item_is_selected(
        self, decoy: Decoy, test_client: TestClient, item_service: ItemService
    ):
        # Arrange
        item_uid = uuid4()
        value = ItemSelect(select=True, dry_run=True)
        decoy.when(item_service.select(item_uid, value)).then_return(
            ItemSelectResult(dry_run=True)
        )

        # Act
        response = test_client.post(
            f"api/items/item/{item_uid}/select",
            json=value.model_dump(mode="json", by_alias=True),
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json()["dryRun"] is True

    @pytest.mark.parametrize(
        ("outcome", "status_code"),
        [
            (NotAllowedActionError("Batch is locked"), HTTPStatus.CONFLICT),
            (None, HTTPStatus.NOT_FOUND),
        ],
    )
    def test_a_selection_that_cannot_be_made_is_refused(
        self,
        decoy: Decoy,
        test_client: TestClient,
        item_service: ItemService,
        outcome: Exception | None,
        status_code: HTTPStatus,
    ):
        # Arrange
        item_uid = uuid4()
        value = ItemSelect(select=False)
        stub = decoy.when(item_service.select(item_uid, value))
        if outcome is None:
            stub.then_return(None)
        else:
            stub.then_raise(outcome)

        # Act
        response = test_client.post(
            f"api/items/item/{item_uid}/select",
            json=value.model_dump(mode="json", by_alias=True),
        )

        # Assert
        assert response.status_code == status_code

    @pytest.mark.parametrize(
        ("outcome", "status_code"),
        [
            (NotAllowedActionError("Batch is locked"), HTTPStatus.CONFLICT),
            (None, HTTPStatus.NOT_FOUND),
        ],
    )
    def test_a_selection_of_many_that_cannot_be_made_is_refused(
        self,
        decoy: Decoy,
        test_client: TestClient,
        item_service: ItemService,
        outcome: Exception | None,
        status_code: HTTPStatus,
    ):
        # Arrange
        value = ItemBulkSelect(item_uids=[uuid4()], select=True)
        stub = decoy.when(item_service.select_many(value))
        if outcome is None:
            stub.then_return(None)
        else:
            stub.then_raise(outcome)

        # Act
        response = test_client.post(
            "api/items/select", json=value.model_dump(mode="json", by_alias=True)
        )

        # Assert
        assert response.status_code == status_code

    def test_selection_trees_that_cannot_be_worked_out_are_refused(
        self, decoy: Decoy, test_client: TestClient, item_service: ItemService
    ):
        # Arrange
        item_uid = uuid4()
        decoy.when(item_service.selection_trees([item_uid], True)).then_raise(
            NotAllowedActionError("Batch is locked")
        )

        # Act
        response = test_client.post(
            "api/items/selection-trees",
            json={"itemUids": [str(item_uid)], "select": True},
        )

        # Assert
        assert response.status_code == HTTPStatus.CONFLICT

    def test_adding_an_item_that_is_not_allowed_is_refused(
        self,
        decoy: Decoy,
        test_client: TestClient,
        item_service: ItemService,
        sample: Sample,
    ):
        # Arrange
        decoy.when(item_service.add(Anything())).then_raise(
            NotAllowedActionError("The project is view only")
        )

        # Act
        response = test_client.post(
            "api/items/add", json=sample.model_dump(mode="json", by_alias=True)
        )

        # Assert
        assert response.status_code == HTTPStatus.CONFLICT

    def test_an_item_is_created_under_the_parents_given(
        self,
        decoy: Decoy,
        test_client: TestClient,
        item_service: ItemService,
        sample: Sample,
    ):
        # Arrange
        parent_uid = uuid4()
        decoy.when(
            item_service.create(
                sample.schema_uid,
                sample.batch_uid,
                target_parent_uids=[parent_uid],
                identifier=sample.identifier,
            )
        ).then_return(sample)

        # Act
        response = test_client.post(
            "api/items/create",
            params={
                "schemaUid": str(sample.schema_uid),
                "batchUid": str(sample.batch_uid),
                "targetParentUids": [str(parent_uid)],
                "identifier": sample.identifier,
            },
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json()["uid"] == str(sample.uid)

    @pytest.mark.parametrize(
        ("outcome", "status_code"),
        [
            (NotAllowedActionError("The project is view only"), HTTPStatus.CONFLICT),
            (None, HTTPStatus.NOT_FOUND),
        ],
    )
    def test_an_item_that_cannot_be_created_is_refused(
        self,
        decoy: Decoy,
        test_client: TestClient,
        item_service: ItemService,
        outcome: Exception | None,
        status_code: HTTPStatus,
    ):
        # Arrange
        schema_uid = uuid4()
        batch_uid = uuid4()
        stub = decoy.when(
            item_service.create(
                schema_uid, batch_uid, target_parent_uids=None, identifier=None
            )
        )
        if outcome is None:
            stub.then_return(None)
        else:
            stub.then_raise(outcome)

        # Act
        response = test_client.post(
            "api/items/create",
            params={"schemaUid": str(schema_uid), "batchUid": str(batch_uid)},
        )

        # Assert
        assert response.status_code == status_code

    def test_an_item_is_copied(
        self,
        decoy: Decoy,
        test_client: TestClient,
        item_service: ItemService,
        sample: Sample,
    ):
        # Arrange
        item_uid = uuid4()
        decoy.when(
            item_service.copy(item_uid, target_parent_uids=None, identifier="copy")
        ).then_return(sample)

        # Act
        response = test_client.post(
            f"api/items/item/{item_uid}/copy", params={"identifier": "copy"}
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json()["uid"] == str(sample.uid)

    @pytest.mark.parametrize(
        ("outcome", "status_code"),
        [
            (NotAllowedActionError("The project is view only"), HTTPStatus.CONFLICT),
            (None, HTTPStatus.NOT_FOUND),
        ],
    )
    def test_an_item_that_cannot_be_copied_is_refused(
        self,
        decoy: Decoy,
        test_client: TestClient,
        item_service: ItemService,
        outcome: Exception | None,
        status_code: HTTPStatus,
    ):
        # Arrange
        item_uid = uuid4()
        stub = decoy.when(
            item_service.copy(item_uid, target_parent_uids=None, identifier=None)
        )
        if outcome is None:
            stub.then_return(None)
        else:
            stub.then_raise(outcome)

        # Act
        response = test_client.post(f"api/items/item/{item_uid}/copy")

        # Assert
        assert response.status_code == status_code

    def test_the_items_of_a_schema_are_got_with_the_table_request_and_count(
        self,
        decoy: Decoy,
        test_client: TestClient,
        item_service: ItemService,
        sample: Sample,
    ):
        # Arrange
        decoy.when(
            item_service.get_for_schema(
                sample.schema_uid,
                sample.dataset_uid,
                None,
                0,
                10,
                "patient",
                False,
                None,
                None,
                None,
                None,
                None,
                None,
                status_filter=None,
            )
        ).then_return([sample])
        decoy.when(
            item_service.get_count_for_schema(
                sample.schema_uid,
                sample.dataset_uid,
                None,
                "patient",
                False,
                None,
                None,
                None,
                None,
                None,
                status_filter=None,
            )
        ).then_return(11)

        # Act
        response = test_client.post(
            "api/items",
            params={
                "datasetUid": str(sample.dataset_uid),
                "itemSchemaUid": str(sample.schema_uid),
            },
            json={"start": 0, "size": 10, "identifierFilter": "patient"},
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json()["count"] == 11
        assert [item["uid"] for item in response.json()["items"]] == [str(sample.uid)]

    def test_the_hierarchy_under_an_item_that_is_not_there_is_not_found(
        self, decoy: Decoy, test_client: TestClient, item_service: ItemService
    ):
        # Arrange
        item_uid = uuid4()
        hierarchy_layout_uid = uuid4()
        decoy.when(
            item_service.get_hierarchy(item_uid, hierarchy_layout_uid)
        ).then_return(None)

        # Act
        response = test_client.get(
            f"api/items/item/{item_uid}/hierarchy/{hierarchy_layout_uid}"
        )

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_the_neighbours_of_an_item_are_got(
        self, decoy: Decoy, test_client: TestClient, item_service: ItemService
    ):
        # Arrange
        item_uid = uuid4()
        batch_uid = uuid4()
        neighbours = ItemNeighbours(previous_uid=uuid4(), next_uid=None)
        decoy.when(item_service.get_neighbours(item_uid, batch_uid, True)).then_return(
            neighbours
        )

        # Act
        response = test_client.get(
            f"api/items/item/{item_uid}/neighbours",
            params={"batchUid": str(batch_uid), "pseudonymMode": "true"},
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json() == neighbours.model_dump(mode="json", by_alias=True)

    def test_a_child_identifier_is_suggested(
        self, decoy: Decoy, test_client: TestClient, item_service: ItemService
    ):
        # Arrange
        item_uid = uuid4()
        item_schema_uid = uuid4()
        suggestion = NewChildSuggestion(identifier="patient 1 block 2")
        decoy.when(item_service.suggest_child(item_schema_uid, item_uid)).then_return(
            suggestion
        )

        # Act
        response = test_client.get(
            f"api/items/item/{item_uid}/suggested-child-identifier",
            params={"itemSchemaUid": str(item_schema_uid)},
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json()["identifier"] == "patient 1 block 2"

    def test_images_gathered_by_neither_a_schema_nor_a_layout_are_refused(
        self, decoy: Decoy, test_client: TestClient, item_service: ItemService
    ):
        # Act
        response = test_client.get(f"api/items/item/{uuid4()}/images")

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST
        decoy.verify(
            item_service.get_images_for_item(Anything(), Anything(), Anything()),
            times=0,
        )

    def test_the_images_of_an_item_are_got_by_layout(
        self, decoy: Decoy, test_client: TestClient, item_service: ItemService
    ):
        # Arrange
        item_uid = uuid4()
        images_layout_uid = uuid4()
        decoy.when(
            item_service.get_images_for_item(item_uid, None, images_layout_uid)
        ).then_return([])

        # Act
        response = test_client.get(
            f"api/items/item/{item_uid}/images",
            params={"imagesLayoutUid": str(images_layout_uid)},
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json() == []

    @pytest.mark.parametrize(
        ("outcome", "status_code"),
        [
            (ValueError("Layout is not an overview"), HTTPStatus.BAD_REQUEST),
            (None, HTTPStatus.NOT_FOUND),
        ],
    )
    def test_an_overview_that_cannot_be_got_is_refused(
        self,
        decoy: Decoy,
        test_client: TestClient,
        overview_service: OverviewService,
        outcome: Exception | None,
        status_code: HTTPStatus,
    ):
        # Arrange
        item_uid = uuid4()
        overview_layout_uid = uuid4()
        stub = decoy.when(
            overview_service.get_overview_data(
                item_uid, overview_layout_uid, False, None, None
            )
        )
        if outcome is None:
            stub.then_return(None)
        else:
            stub.then_raise(outcome)

        # Act
        response = test_client.get(
            f"api/items/item/{item_uid}/overview/{overview_layout_uid}"
        )

        # Assert
        assert response.status_code == status_code

    def test_an_item_is_moved_to_another_parent(
        self,
        decoy: Decoy,
        test_client: TestClient,
        item_service: ItemService,
        sample: Sample,
    ):
        # Arrange
        target_parent_uid = uuid4()
        decoy.when(
            item_service.move_to_parent(sample.uid, target_parent_uid)
        ).then_return(sample)

        # Act
        response = test_client.post(
            f"api/items/item/{sample.uid}/move",
            params={"targetParentUid": str(target_parent_uid)},
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.json()["uid"] == str(sample.uid)

    def test_a_move_the_service_refuses_is_a_bad_request(
        self, decoy: Decoy, test_client: TestClient, item_service: ItemService
    ):
        # Arrange
        item_uid = uuid4()
        target_parent_uid = uuid4()
        decoy.when(item_service.move_to_parent(item_uid, target_parent_uid)).then_raise(
            ValueError("Parent is of the wrong schema")
        )

        # Act
        response = test_client.post(
            f"api/items/item/{item_uid}/move",
            params={"targetParentUid": str(target_parent_uid)},
        )

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json()["detail"] == "Parent is of the wrong schema"

    def test_an_attribute_is_moved_between_items(
        self, decoy: Decoy, test_client: TestClient, item_service: ItemService
    ):
        # Arrange
        request = MoveAttributeRequest(
            source_item_uid=uuid4(), attribute_tag="stain", target_item_uid=uuid4()
        )

        # Act
        response = test_client.post(
            "api/items/move-attribute",
            json=request.model_dump(mode="json", by_alias=True),
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        decoy.verify(
            item_service.move_attribute(
                request.source_item_uid,
                request.attribute_tag,
                target_item_uid=request.target_item_uid,
            ),
            times=1,
        )

    def test_an_attribute_move_the_service_refuses_is_a_bad_request(
        self, decoy: Decoy, test_client: TestClient, item_service: ItemService
    ):
        # Arrange
        request = MoveAttributeRequest(
            source_item_uid=uuid4(), attribute_tag="stain", target_item_uid=uuid4()
        )
        decoy.when(
            item_service.move_attribute(
                request.source_item_uid,
                request.attribute_tag,
                target_item_uid=request.target_item_uid,
            )
        ).then_raise(ValueError("No such attribute"))

        # Act
        response = test_client.post(
            "api/items/move-attribute",
            json=request.model_dump(mode="json", by_alias=True),
        )

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST

    @pytest.mark.parametrize("path", ["remap", "remap_hierarchy"])
    def test_a_remap_of_an_item_that_is_not_there_is_not_found(
        self,
        decoy: Decoy,
        test_client: TestClient,
        item_service: ItemService,
        mapper_service: MapperService,
        path: str,
    ):
        # Arrange
        item_uid = uuid4()
        decoy.when(item_service.get_optional(item_uid)).then_return(None)

        # Act
        response = test_client.post(f"api/items/item/{item_uid}/{path}")

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND
        decoy.verify(mapper_service.remap_item(Anything()), times=0)
        decoy.verify(mapper_service.remap_item_hierarchy(Anything()), times=0)

    def test_an_item_is_remapped(
        self,
        decoy: Decoy,
        test_client: TestClient,
        item_service: ItemService,
        mapper_service: MapperService,
        sample: Sample,
    ):
        # Arrange
        decoy.when(item_service.get_optional(sample.uid)).then_return(sample)

        # Act
        response = test_client.post(f"api/items/item/{sample.uid}/remap")

        # Assert
        assert response.status_code == HTTPStatus.OK
        decoy.verify(mapper_service.remap_item(sample.uid), times=1)

    def test_the_hierarchy_of_an_item_is_remapped(
        self,
        decoy: Decoy,
        test_client: TestClient,
        item_service: ItemService,
        mapper_service: MapperService,
        sample: Sample,
    ):
        # Arrange
        decoy.when(item_service.get_optional(sample.uid)).then_return(sample)

        # Act
        response = test_client.post(f"api/items/item/{sample.uid}/remap_hierarchy")

        # Assert
        assert response.status_code == HTTPStatus.OK
        decoy.verify(mapper_service.remap_item_hierarchy(sample.uid), times=1)
