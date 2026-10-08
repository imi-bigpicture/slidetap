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

"""Writing the planned migration of a project to the database."""

import dataclasses
from collections.abc import Iterable, Mapping
from uuid import UUID

from sqlalchemy.orm import Session

from slidetap.database import (
    DatabaseAttribute,
    DatabaseAttributeMigrationIssue,
    DatabaseDataset,
    DatabaseItem,
    DatabaseProject,
)
from slidetap.external_interfaces.implementations.migration import (
    UnchangedAttributeMigrator,
)
from slidetap.model import (
    AnyAttribute,
    AttributeSchema,
    Dataset,
    Item,
    Project,
    UnresolvedAttributeMigration,
)
from slidetap.services.attribute_service import AttributeService
from slidetap.services.database_service import DatabaseService
from slidetap.services.project_migration_planner import (
    ObjectInMigration,
    ProjectMigrationPlanner,
    SearchItemInMigration,
)
from slidetap.services.review_service import ReviewService
from slidetap.services.validation_service import ValidationService


class ProjectMigrationExecutor:
    """Writes the migration of a project in a session: puts the resolved values
    at their tags, replaces the attributes of every object, moves the search
    items and the project to the target root, and validates the project again.
    """

    def __init__(
        self,
        session: Session,
        database_service: DatabaseService,
        attribute_service: AttributeService,
        validation_service: ValidationService,
        review_service: ReviewService,
    ):
        """Create the executor of a migration.

        Parameters
        ----------
        session: Session
            The session to write the migration in.
        database_service: DatabaseService
            For the rows of the project.
        attribute_service: AttributeService
            For the display values of attributes.
        validation_service: ValidationService
            For validating the project on the target root.
        review_service: ReviewService
            For flagging review units left invalid.
        """
        self._session = session
        self._database_service = database_service
        self._attribute_service = attribute_service
        self._validation_service = validation_service
        self._review_service = review_service

    def write(
        self,
        project: DatabaseProject,
        target_root_schema_uid: UUID,
        objects: Iterable[ObjectInMigration],
        search_items: Iterable[SearchItemInMigration],
        issues: Mapping[tuple[UUID, str], DatabaseAttributeMigrationIssue],
    ) -> None:
        """Put the resolved values at their tags, replace the attributes of
        every object, and move the search items and the project to the target
        root.

        Parameters
        ----------
        project: DatabaseProject
            The project.
        target_root_schema_uid: UUID
            The uid of the root the project is migrated to.
        objects: Iterable[ObjectInMigration]
            The project, the dataset, and the items, checked.
        search_items: Iterable[SearchItemInMigration]
            The search items of the project, with their target item schemas.
        issues: Mapping[tuple[UUID, str], DatabaseAttributeMigrationIssue]
            The resolved attribute issues with a target, by object uid and
            target tag, with one for each unresolved attribute.

        Raises
        ------
        MigrationError
            If an attribute is not on the attribute schema of its tag.
        """
        for object_ in objects:
            self._write_object(self._apply_resolutions(object_, issues))
        for search_item in search_items:
            row = self._database_service.get_metadata_search_item(
                self._session, search_item.source.uid
            )
            row.schema_uid = search_item.target_schema.uid
        project.root_schema_uid = target_root_schema_uid

    def revalidate(self, project: DatabaseProject) -> None:
        """Validate the whole project again, on the root it is on, and flag the
        review units left invalid.

        Parameters
        ----------
        project: DatabaseProject
            The project.
        """
        session = self._session
        dataset = self._database_service.get_dataset(session, project.dataset_uid)
        self._validation_service.validate_project_attributes(project, session)
        self._validation_service.validate_dataset_attributes(dataset, session)
        for item in self._database_service.get_items_in_dataset(session, dataset.uid):
            self._validation_service.validate_item(item, session)
        self._review_service.flag_invalid_review_units(dataset.uid, session=session)

    @staticmethod
    def _apply_resolutions(
        object_: ObjectInMigration,
        issues: Mapping[tuple[UUID, str], DatabaseAttributeMigrationIssue],
    ) -> ObjectInMigration:
        """Put the resolved values at their tags, and nothing at a tag left
        empty.

        A resolved value is given the uid of the attribute it resolves, as the
        migration gives a converted one, keeping the row of the attribute and
        its lock and read only flags.

        Parameters
        ----------
        object_: ObjectInMigration
            The object, checked.
        issues: Mapping[tuple[UUID, str], DatabaseAttributeMigrationIssue]
            The resolved attribute issues with a target, by object uid and
            target tag, with one for each unresolved attribute of the object.

        Returns
        -------
        ObjectInMigration
            The object, with the resolved values and nothing unresolved.
        """
        resolved_mappings: list[
            dict[str, AnyAttribute | UnresolvedAttributeMigration]
        ] = []
        for attributes in (
            object_.target_attributes,
            object_.target_private_attributes,
        ):
            resolved_attributes: dict[
                str, AnyAttribute | UnresolvedAttributeMigration
            ] = {}
            for tag, attribute in attributes.items():
                if not isinstance(attribute, UnresolvedAttributeMigration):
                    resolved_attributes[tag] = attribute
                    continue
                resolved = issues[(object_.source.uid, tag)].resolved
                if resolved is None:
                    continue
                replaced = attribute.original or attribute.proposed
                if replaced is not None:
                    resolved = resolved.model_copy(update={"uid": replaced.uid})
                resolved_attributes[tag] = resolved
            resolved_mappings.append(resolved_attributes)
        attributes, private_attributes = resolved_mappings
        return dataclasses.replace(
            object_,
            target_attributes=attributes,
            target_private_attributes=private_attributes,
        )

    def _write_object(
        self, object_: ObjectInMigration
    ) -> DatabaseProject | DatabaseDataset | DatabaseItem:
        """Put an object on its target schema, and replace its attributes with
        the target ones.

        The old rows are deleted and the target attributes inserted, keeping
        their uids, and with them the locks and read only flags of the rows of
        the same uid. The only rows referring to attribute rows are unmapped
        values, which go with them and are recorded again for the new rows.

        Parameters
        ----------
        object_: ObjectInMigration
            The object, with the resolved values and nothing unresolved.

        Returns
        -------
        DatabaseProject | DatabaseDataset | DatabaseItem
            The row of the object, written.

        Raises
        ------
        MigrationError
            If an attribute is not on the attribute schema of its tag.
        """
        row = self._get_object_row(object_.source)
        target_schema = object_.target_schema
        old_rows: list[DatabaseAttribute] = [
            *row.attributes,
            *row.private_attributes,
        ]
        flags = {old.uid: (old.read_only, old.locked) for old in old_rows}
        if old_rows:
            # Deleted with them by the database, but said here for a database
            # that does not enforce its foreign keys.
            self._database_service.delete_unmapped_values(self._session, list(flags))
        row.attributes = set()
        row.private_attributes = set()
        self._session.flush()
        row.schema_uid = target_schema.uid
        row.attributes = self._add_attributes(
            row,
            ProjectMigrationPlanner.get_migrated_attributes(object_.target_attributes),
            target_schema.attributes,
            flags,
        )
        row.private_attributes = self._add_attributes(
            row,
            ProjectMigrationPlanner.get_migrated_attributes(
                object_.target_private_attributes
            ),
            target_schema.private_attributes,
            flags,
        )
        return row

    def _get_object_row(
        self, source: Project | Dataset | Item
    ) -> DatabaseProject | DatabaseDataset | DatabaseItem:
        """Get the row of an object.

        Parameters
        ----------
        source: Project | Dataset | Item
            The object.

        Returns
        -------
        DatabaseProject | DatabaseDataset | DatabaseItem
            The row of the object.
        """
        if isinstance(source, Project):
            return self._database_service.get_project(self._session, source)
        if isinstance(source, Dataset):
            return self._database_service.get_dataset(self._session, source)
        return self._database_service.get_item(self._session, source)

    def _add_attributes(
        self,
        row: DatabaseProject | DatabaseDataset | DatabaseItem,
        attributes: Mapping[str, AnyAttribute],
        schemas: Mapping[str, AttributeSchema],
        flags: Mapping[UUID, tuple[bool, bool]],
    ) -> set[DatabaseAttribute]:
        """Add the rows of the target attributes of an object.

        Parameters
        ----------
        row: DatabaseProject | DatabaseDataset | DatabaseItem
            The row of the object.
        attributes: Mapping[str, AnyAttribute]
            The target attributes, by tag.
        schemas: Mapping[str, AttributeSchema]
            The attribute schemas of the target schema, by tag.
        flags: Mapping[UUID, tuple[bool, bool]]
            The read only and locked flags of the old rows, by uid.

        Returns
        -------
        set[DatabaseAttribute]
            The added rows.

        Raises
        ------
        MigrationError
            If an attribute is not on the attribute schema of its tag.
        """
        rows: set[DatabaseAttribute] = set()
        for tag, attribute in attributes.items():
            schema = ProjectMigrationPlanner.refuse_attribute_off_schema(
                row.uid, tag, attribute, schemas.get(tag)
            )
            # Mapping items a mapper move removed are referred to by nothing.
            attribute = UnchangedAttributeMigrator.without_mapping_items(
                attribute,
                lambda uid: (
                    self._database_service.get_optional_mapping(self._session, uid)
                    is None
                ),
            )
            self._attribute_service.set_display_value(attribute)
            attribute_row = self._database_service.add_attribute(
                self._session, attribute, schema
            )
            attribute_row.rejected = attribute.rejected
            attribute_row.read_only, attribute_row.locked = flags.get(
                attribute.uid, (False, False)
            )
            rows.add(attribute_row)
        return rows
