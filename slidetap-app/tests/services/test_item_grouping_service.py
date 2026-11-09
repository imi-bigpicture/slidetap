#    Copyright 2026 SECTRA AB
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

"""Tests for `ItemGroupingService`.

Against a real SQLite database, as what the application is given to group is
what the queries find: the selected items of the project, or of a batch.
"""

import datetime
from collections import defaultdict
from collections.abc import Callable, Collection, Mapping, Sequence
from uuid import UUID, uuid4

import pytest
from slidetap_example import ExampleSchema

from slidetap.external_interfaces import ItemGrouper
from slidetap.model import (
    AnyItem,
    BatchCreate,
    Dataset,
    IncompleteItem,
    ItemGroup,
    ItemGroupingPolicy,
    ItemGroups,
    NotFoundError,
    Project,
    ReviewLayout,
    ReviewUnitSchema,
    RootSchema,
    Sample,
)
from slidetap.services import DatabaseService, ItemGroupingService, SchemaService


class GroupingByName(ItemGrouper):
    """Groups the specimens by their name, counting each as one; a specimen
    without a name is in none. Keeps what it was given."""

    def __init__(self, specimen_schema_uid: UUID):
        self._specimen_schema_uid = specimen_schema_uid
        self.given: Mapping[UUID, Sequence[AnyItem]] = {}

    def schema_uids(self) -> Collection[UUID]:
        return [self._specimen_schema_uid]

    def group(self, items: Mapping[UUID, Sequence[AnyItem]]) -> ItemGroups:
        self.given = items
        by_name: dict[str, list[UUID]] = defaultdict(list)
        incomplete: list[IncompleteItem] = []
        for item in items[self._specimen_schema_uid]:
            if item.name is None:
                incomplete.append(IncompleteItem(item_uid=item.uid, missing=["Name"]))
            else:
                by_name[item.name].append(item.uid)
        return ItemGroups(
            columns=["Name"],
            groups=[
                ItemGroup(values=[name], item_uids=uids, count=len(uids))
                for name, uids in by_name.items()
            ],
            incomplete=incomplete,
        )


class GroupingReading(GroupingByName):
    """Groups by name, but names the schemas it is given as told."""

    def __init__(self, specimen_schema_uid: UUID, read: Collection[UUID]):
        super().__init__(specimen_schema_uid)
        self._read = read

    def schema_uids(self) -> Collection[UUID]:
        return self._read


@pytest.fixture()
def policy(schema: ExampleSchema) -> ItemGroupingPolicy | None:
    return ItemGroupingPolicy(
        schema_uid=schema.specimen_schema_uid,
        minimum_count=2,
        count_display_name="Specimens",
    )


@pytest.fixture()
def root(schema: ExampleSchema, policy: ItemGroupingPolicy | None) -> RootSchema:
    return schema.model_copy(update={"item_grouping": policy})


@pytest.fixture()
def grouping(schema: ExampleSchema) -> GroupingByName | None:
    return GroupingByName(schema.specimen_schema_uid)


@pytest.fixture()
def schema_service(
    root: RootSchema,
    grouping: GroupingByName | None,
    schema_service_of: Callable[..., SchemaService],
) -> SchemaService:
    return schema_service_of(
        root, item_groupers={root.uid: grouping} if grouping else None
    )


@pytest.fixture()
def service(
    schema_service: SchemaService, stored_database_service: DatabaseService
) -> ItemGroupingService:
    return ItemGroupingService(schema_service, stored_database_service)


class Stored:
    """Projects with batches of specimens, in the database."""

    def __init__(self, database_service: DatabaseService, root: RootSchema):
        self._database_service = database_service
        self._root = root

    def project(self) -> UUID:
        dataset = Dataset(
            uid=uuid4(), name="dataset", schema_uid=self._root.dataset.uid
        )
        project = Project(
            uid=uuid4(),
            name="project",
            root_schema_uid=self._root.uid,
            schema_uid=self._root.project.uid,
            dataset_uid=dataset.uid,
            created=datetime.datetime(2026, 1, 1),
        )
        with self._database_service.get_session() as session:
            self._database_service.add_dataset(session, dataset)
            self._database_service.add_project(session, project)
            session.commit()
        return project.uid

    def batch(self, project_uid: UUID, name: str = "batch") -> UUID:
        with self._database_service.get_session() as session:
            batch = self._database_service.add_batch(
                session, BatchCreate(name=name, project_uid=project_uid)
            )
            session.commit()
            return batch.uid

    def specimen(
        self,
        schema: ExampleSchema,
        batch_uid: UUID,
        name: str | None,
        selected: bool = True,
        schema_uid: UUID | None = None,
    ) -> UUID:
        with self._database_service.get_session() as session:
            batch = self._database_service.get_batch(session, batch_uid)
            specimen = Sample(
                uid=uuid4(),
                identifier=f"specimen-{uuid4().hex[:6]}",
                name=name,
                dataset_uid=batch.project.dataset_uid,
                batch_uid=batch_uid,
                schema_uid=schema_uid or schema.specimen_schema_uid,
            )
            added = self._database_service.add_item(session, specimen, [], [])
            # Selection is set after adding, as the import does not deselect.
            added.selected = selected
            session.commit()
            return specimen.uid


@pytest.fixture()
def stored(stored_database_service: DatabaseService, root: RootSchema) -> Stored:
    return Stored(stored_database_service, root)


@pytest.mark.unittest
class TestItemGroupingService:
    def test_groups_are_listed_smallest_first_with_those_too_small_marked(
        self, service: ItemGroupingService, stored: Stored, schema: ExampleSchema
    ):
        # Arrange
        project = stored.project()
        batch = stored.batch(project)
        for _ in range(3):
            stored.specimen(schema, batch, "large")
        small = stored.specimen(schema, batch, "small")

        # Act
        grouping = service.get_grouping(project)

        # Assert
        assert grouping is not None
        assert grouping.columns == ["Name"]
        assert [group.values for group in grouping.groups] == [["small"], ["large"]]
        assert [group.below_minimum for group in grouping.groups] == [True, False]
        assert [item.uid for item in grouping.groups[0].items] == [small]
        assert grouping.groups[0].items[0].batch_name == "batch"

    def test_groups_of_the_same_size_are_listed_by_their_values(
        self, service: ItemGroupingService, stored: Stored, schema: ExampleSchema
    ):
        # Arrange
        project = stored.project()
        batch = stored.batch(project)
        for name in ["c", "a", "b"]:
            stored.specimen(schema, batch, name)

        # Act
        grouping = service.get_grouping(project)

        # Assert
        assert grouping is not None
        assert [group.values for group in grouping.groups] == [["a"], ["b"], ["c"]]

    def test_items_not_selected_are_not_grouped(
        self,
        service: ItemGroupingService,
        stored: Stored,
        schema: ExampleSchema,
        grouping: GroupingByName,
    ):
        # Arrange
        project = stored.project()
        batch = stored.batch(project)
        kept = stored.specimen(schema, batch, "kept")
        stored.specimen(schema, batch, "left out", selected=False)

        # Act
        service.get_grouping(project)

        # Assert
        given = grouping.given[schema.specimen_schema_uid]
        assert [item.uid for item in given] == [kept]

    def test_a_batch_groups_only_its_own_items(
        self,
        service: ItemGroupingService,
        stored: Stored,
        schema: ExampleSchema,
    ):
        # Arrange
        project = stored.project()
        first = stored.batch(project, "first")
        second = stored.batch(project, "second")
        stored.specimen(schema, first, "shared")
        stored.specimen(schema, second, "shared")

        # Act
        of_project = service.get_grouping(project)
        of_batch = service.get_grouping(project, first)

        # Assert
        assert of_project is not None and of_batch is not None
        assert [group.count for group in of_project.groups] == [2]
        assert [group.count for group in of_batch.groups] == [1]
        assert of_batch.batch_uid == first

    def test_a_batch_is_given_the_items_read_by_of_every_batch(
        self,
        schema_service_of: Callable[..., SchemaService],
        stored_database_service: DatabaseService,
        stored: Stored,
        schema: ExampleSchema,
        root: RootSchema,
    ):
        # Arrange
        project = stored.project()
        first = stored.batch(project, "first")
        second = stored.batch(project, "second")
        stored.specimen(schema, first, "grouped")
        stored.specimen(schema, second, "not of the batch")
        case = stored.specimen(
            schema, second, "case", schema_uid=schema.case_schema_uid
        )
        grouping = GroupingReading(
            schema.specimen_schema_uid,
            [schema.specimen_schema_uid, schema.case_schema_uid],
        )
        service = ItemGroupingService(
            schema_service_of(root, item_groupers={root.uid: grouping}),
            stored_database_service,
        )

        # Act
        service.get_grouping(project, first)

        # Assert
        assert [item.name for item in grouping.given[schema.specimen_schema_uid]] == [
            "grouped"
        ]
        assert [item.uid for item in grouping.given[schema.case_schema_uid]] == [case]

    def test_items_in_no_group_are_listed_named(
        self, service: ItemGroupingService, stored: Stored, schema: ExampleSchema
    ):
        # Arrange
        project = stored.project()
        batch = stored.batch(project)
        unnamed = stored.specimen(schema, batch, None)

        # Act
        grouping = service.get_grouping(project)

        # Assert
        assert grouping is not None
        assert [entry.item.uid for entry in grouping.incomplete] == [unnamed]
        assert grouping.incomplete[0].missing == ["Name"]

    def test_a_batch_of_another_project_is_not_found(
        self, service: ItemGroupingService, stored: Stored
    ):
        # Arrange
        project = stored.project()
        other_batch = stored.batch(stored.project())

        # Act / Assert
        with pytest.raises(NotFoundError):
            service.get_grouping(project, other_batch)

    def test_a_batch_that_does_not_exist_is_not_found(
        self, service: ItemGroupingService, stored: Stored
    ):
        # Arrange
        project = stored.project()

        # Act / Assert
        with pytest.raises(NotFoundError):
            service.get_grouping(project, uuid4())

    def test_a_project_that_does_not_exist_is_not_found(
        self, service: ItemGroupingService, stored: Stored
    ):
        # Arrange
        stored.project()

        # Act / Assert
        with pytest.raises(NotFoundError):
            service.get_grouping(uuid4())

    @pytest.mark.parametrize("policy", [None])
    def test_a_root_without_a_policy_groups_nothing(
        self, service: ItemGroupingService, stored: Stored
    ):
        # Arrange
        project = stored.project()

        # Act
        grouping = service.get_grouping(project)

        # Assert
        assert grouping is None

    @pytest.mark.parametrize("grouping", [None])
    def test_an_application_without_a_grouping_groups_nothing(
        self, service: ItemGroupingService, stored: Stored
    ):
        # Arrange
        project = stored.project()

        # Act
        grouping = service.get_grouping(project)

        # Assert
        assert grouping is None


@pytest.mark.unittest
class TestItemGroupersOfRoots:
    def test_a_grouper_of_a_root_without_a_policy_is_not_used(
        self,
        schema: ExampleSchema,
        schema_service_of: Callable[..., SchemaService],
    ):
        # Arrange
        grouping = GroupingByName(schema.specimen_schema_uid)

        # Act
        schema_service = schema_service_of(schema, item_groupers={schema.uid: grouping})

        # Assert
        assert schema_service.item_grouper_of(schema.uid) is None

    def test_a_grouper_reading_a_schema_the_root_lacks_is_refused(
        self,
        root: RootSchema,
        schema: ExampleSchema,
        schema_service_of: Callable[..., SchemaService],
    ):
        # Arrange
        grouping = GroupingReading(
            schema.specimen_schema_uid, [schema.specimen_schema_uid, uuid4()]
        )

        # Act & Assert
        with pytest.raises(ValueError, match="not item schemas of it"):
            schema_service_of(root, item_groupers={root.uid: grouping})

    def test_a_grouper_not_reading_the_schema_of_the_policy_is_refused(
        self,
        root: RootSchema,
        schema: ExampleSchema,
        schema_service_of: Callable[..., SchemaService],
    ):
        # Arrange
        grouping = GroupingReading(schema.specimen_schema_uid, [schema.case_schema_uid])

        # Act & Assert
        with pytest.raises(ValueError, match="does not read"):
            schema_service_of(root, item_groupers={root.uid: grouping})


@pytest.mark.unittest
class TestReviewUnitsOfGroups:
    @pytest.fixture()
    def root(
        self, schema: ExampleSchema, policy: ItemGroupingPolicy | None
    ) -> RootSchema:
        """The example root with the case as the review unit."""
        return schema.model_copy(
            update={
                "item_grouping": policy,
                "review_unit": ReviewUnitSchema(
                    schema_uid=schema.case_schema_uid,
                    layout=ReviewLayout(uid=uuid4(), name="review"),
                ),
            }
        )

    def test_a_group_names_the_cases_of_its_items_once_each(
        self,
        service: ItemGroupingService,
        stored: Stored,
        schema: ExampleSchema,
        stored_database_service: DatabaseService,
    ):
        # Arrange
        project = stored.project()
        batch = stored.batch(project)
        with stored_database_service.get_session() as session:
            database_batch = stored_database_service.get_batch(session, batch)
            case = Sample(
                uid=uuid4(),
                identifier="case",
                dataset_uid=database_batch.project.dataset_uid,
                batch_uid=batch,
                schema_uid=schema.case_schema_uid,
            )
            stored_database_service.add_item(session, case, [], [])
            session.flush()
            for number in (1, 2):
                stored_database_service.add_item(
                    session,
                    Sample(
                        uid=uuid4(),
                        identifier=f"case-{number}",
                        name="same",
                        dataset_uid=database_batch.project.dataset_uid,
                        batch_uid=batch,
                        schema_uid=schema.specimen_schema_uid,
                        parents={schema.case_to_specimen_relation.uid: [case.uid]},
                    ),
                    [],
                    [],
                )
            session.commit()

        # Act
        grouping = service.get_grouping(project)

        # Assert
        assert grouping is not None
        assert grouping.groups[0].review_unit_uids == [case.uid]


@pytest.mark.unittest
class TestItemsFilteredByUid:
    def test_only_the_items_asked_for_are_found_and_counted(
        self,
        stored: Stored,
        schema: ExampleSchema,
        stored_database_service: DatabaseService,
        root: RootSchema,
    ):
        # Arrange
        project = stored.project()
        batch = stored.batch(project)
        wanted = stored.specimen(schema, batch, "wanted")
        stored.specimen(schema, batch, "other")
        specimen_schema = root.samples[schema.specimen_schema_uid]

        # Act
        with stored_database_service.get_session() as session:
            found = [
                item.uid
                for item in stored_database_service.get_samples(
                    session, specimen_schema, uids=[wanted]
                )
            ]
            count = stored_database_service.get_item_count(
                session, specimen_schema, uids=[wanted]
            )

        # Assert
        assert found == [wanted]
        assert count == 1


@pytest.mark.unittest
class TestItemGroupingPolicy:
    def test_a_close_count_below_the_minimum_is_refused(self, schema: ExampleSchema):
        # Arrange
        schema_uid = schema.specimen_schema_uid

        # Act / Assert
        with pytest.raises(ValueError, match="close_count"):
            ItemGroupingPolicy(schema_uid=schema_uid, minimum_count=11, close_count=10)

    def test_a_close_count_from_the_minimum_is_kept(self, schema: ExampleSchema):
        # Arrange
        schema_uid = schema.specimen_schema_uid

        # Act
        policy = ItemGroupingPolicy(
            schema_uid=schema_uid, minimum_count=11, close_count=11
        )

        # Assert
        assert policy.close_count == 11
