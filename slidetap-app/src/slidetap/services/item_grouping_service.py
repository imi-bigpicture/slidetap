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

"""Service for the groups the items of a project fall into, see
`ItemGroupingPolicy`."""

import logging
import time
from collections.abc import Mapping, Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from slidetap.database import DatabaseItem
from slidetap.model import (
    AnyItem,
    IncompleteGroupedItem,
    ItemGrouping,
    ItemGroupSummary,
    NotFoundError,
)
from slidetap.model.schema.root_schema_index import RootSchemaIndex
from slidetap.services.database_service import DatabaseService
from slidetap.services.schema_service import SchemaService


class ItemGroupingService:
    """The groups of the selected items of a project, or of one of its
    batches, as the application's `ItemGrouper` of the root works them out.

    Worked out when asked rather than stored: a change to one item can move
    it from one group to another, and so change whether groups of items
    nobody touched are large enough.
    """

    def __init__(
        self,
        schema_service: SchemaService,
        database_service: DatabaseService,
    ):
        self._schema_service = schema_service
        self._database_service = database_service
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def get_grouping(
        self,
        project_uid: UUID,
        batch_uid: UUID | None = None,
        session: Session | None = None,
    ) -> ItemGrouping | None:
        """The groups of the selected items of the project, or of the batch
        where given, smallest first.

        None where the root of the project has no grouping policy, or the
        application no grouper for it.

        Raises
        ------
        NotFoundError
            If there is no such project, or the batch is not one of it.
        """
        with self._database_service.get_session(session) as session:
            project = self._database_service.get_optional_project(session, project_uid)
            if project is None:
                raise NotFoundError(f"There is no project {project_uid}.")
            if batch_uid is not None:
                batch = self._database_service.get_optional_batch(session, batch_uid)
                if batch is None or batch.project_uid != project.uid:
                    raise NotFoundError(
                        f"Batch {batch_uid} is not one of project {project_uid}."
                    )
            root = self._schema_service.get_root(project.root_schema_uid)
            policy = root.schema.item_grouping
            grouper = self._schema_service.item_grouper_of(root.uid)
            if policy is None or grouper is None:
                return None
            started = time.perf_counter()
            database = self._database_service
            loaded = {
                schema_uid: database.get_selected_items_with_models_loaded(
                    session,
                    project.dataset_uid,
                    schema_uid,
                    # Only the grouped items are of the batch: what they are
                    # grouped by can be read from an item of another, such as
                    # a patient shared between two.
                    batch_uid if schema_uid == policy.schema_uid else None,
                )
                for schema_uid in grouper.schema_uids()
            }
            queried = time.perf_counter()
            items: Mapping[UUID, Sequence[AnyItem]] = {
                schema_uid: [item.model for item in by_uid.values()]
                for schema_uid, by_uid in loaded.items()
            }
            modelled = time.perf_counter()
            groups = grouper.group(items)
            grouped_at = time.perf_counter()
            grouped = loaded.get(policy.schema_uid, {})
            unit_uid_of = self._review_unit_uids(root, policy.schema_uid, grouped)
            summaries = [
                ItemGroupSummary(
                    values=group.values,
                    parts=group.parts,
                    items=[
                        grouped[uid].identity
                        for uid in group.item_uids
                        if uid in grouped
                    ],
                    count=group.count,
                    review_unit_uids=list(
                        dict.fromkeys(
                            unit_uid_of[uid]
                            for uid in group.item_uids
                            if uid in unit_uid_of
                        )
                    ),
                    below_minimum=group.count < policy.minimum_count,
                )
                for group in groups.groups
            ]
            # Worked out on every visit, so how long it takes, and on how
            # many items, is worth being able to tell.
            self._logger.info(
                f"Grouped {len(loaded.get(policy.schema_uid, {}))} items of "
                f"project {project_uid}"
                + (f", batch {batch_uid}" if batch_uid is not None else "")
                + f", reading {sum(len(by_uid) for by_uid in loaded.values())} "
                f"items: {queried - started:.2f}s querying, "
                f"{modelled - queried:.2f}s making models, "
                f"{grouped_at - modelled:.2f}s grouping, "
                f"{time.perf_counter() - grouped_at:.2f}s summarising."
            )
            return ItemGrouping(
                policy=policy,
                batch_uid=batch_uid,
                columns=groups.columns,
                # Ties by their values, so that groups the same size come
                # in the same order each time, and keep the number a client
                # gives them.
                groups=sorted(
                    summaries, key=lambda summary: (summary.count, summary.values)
                ),
                incomplete=[
                    IncompleteGroupedItem(
                        item=grouped[item.item_uid].identity, missing=item.missing
                    )
                    for item in groups.incomplete
                    if item.item_uid in grouped
                ],
            )

    def _review_unit_uids(
        self,
        root: RootSchemaIndex,
        schema_uid: UUID,
        items: Mapping[UUID, DatabaseItem],
    ) -> dict[UUID, UUID]:
        """The review unit each item is answered for in, by item uid: the item
        itself where its schema is the unit, the nearest unit above it
        otherwise. Left out for an item under no unit."""
        unit = root.review_unit
        if unit is None or not root.review_unit_covers(schema_uid):
            return {}
        if unit.schema_uid == schema_uid:
            return {uid: uid for uid in items}
        found: dict[UUID, UUID] = {}
        for uid, item in items.items():
            ancestor = self._database_service.get_ancestor(item, {unit.schema_uid})
            if ancestor is not None:
                found[uid] = ancestor.uid
        return found
