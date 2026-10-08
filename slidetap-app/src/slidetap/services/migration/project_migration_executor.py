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
from collections.abc import Mapping
from uuid import UUID

from sqlalchemy.orm import Session

from slidetap.database import (
    DatabaseAttribute,
    DatabaseAttributeMigrationIssue,
    DatabaseDataset,
    DatabaseItem,
    DatabaseProject,
)
from slidetap.model import (
    AnyAttribute,
    AttributeSchema,
    Dataset,
    Item,
    Project,
    RootSchemaIndex,
    UnresolvedAttributeMigration,
)
from slidetap.services.attribute_service import AttributeService
from slidetap.services.database_service import DatabaseService
from slidetap.services.migration.project_migration_planner import (
    ObjectInMigration,
    ProjectMigrationPlan,
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
        database_service: DatabaseService,
        attribute_service: AttributeService,
        validation_service: ValidationService,
        review_service: ReviewService,
    ):
        """Create the executor.

        Parameters
        ----------
        database_service: DatabaseService
            For the rows of the project.
        attribute_service: AttributeService
            For the display values of attributes.
        validation_service: ValidationService
            For validating the project on the target root.
        review_service: ReviewService
            For flagging review units left invalid.
        """
        self._database_service = database_service
        self._attribute_service = attribute_service
        self._validation_service = validation_service
        self._review_service = review_service

    def execute(
        self,
        session: Session,
        database_project: DatabaseProject,
        plan: ProjectMigrationPlan,
        resolutions: Mapping[tuple[UUID, UUID], DatabaseAttributeMigrationIssue],
    ) -> None:
        """Put the resolved values at their tags, replace the attributes of
        every object, and move the search items and the project to the target
        root.

        Parameters
        ----------
        session: Session
            The session to write the migration in.
        database_project: DatabaseProject
            The project.
        plan: ProjectMigrationPlan
            The migration of the project, planned again.
        resolutions: Mapping[tuple[UUID, UUID], DatabaseAttributeMigrationIssue]
            The resolved attribute issues with a target, by object uid and
            target attribute schema uid, with one for each unresolved
            attribute.

        Raises
        ------
        MigrationError
            If an attribute is not on the attribute schema of its tag.
        """
        for object_ in plan.objects:
            self._write_object(session, self._apply_resolutions(object_, resolutions))
        for search_item in plan.search_items:
            database_search_item = self._database_service.get_metadata_search_item(
                session, search_item.source.uid
            )
            database_search_item.schema_uid = search_item.target_schema.uid
        database_project.root_schema_uid = plan.target_root.uid

    def revalidate(self, session: Session, database_project: DatabaseProject) -> None:
        """Validate the whole project again, on the root it is on, and flag the
        review units left invalid.

        Parameters
        ----------
        session: Session
            The session to validate the project in.
        database_project: DatabaseProject
            The project.
        """
        database_dataset = self._database_service.get_dataset(
            session, database_project.dataset_uid
        )
        self._validation_service.validate_project_attributes(database_project, session)
        self._validation_service.validate_dataset_attributes(database_dataset, session)
        for database_item in self._database_service.get_items_in_dataset(
            session, database_dataset.uid
        ):
            self._validation_service.validate_item(database_item, session)
        self._review_service.flag_invalid_review_units(
            database_dataset.uid, session=session
        )

    @staticmethod
    def _apply_resolutions(
        object_: ObjectInMigration,
        resolutions: Mapping[tuple[UUID, UUID], DatabaseAttributeMigrationIssue],
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
        resolutions: Mapping[tuple[UUID, UUID], DatabaseAttributeMigrationIssue]
            The resolved attribute issues with a target, by object uid and
            target attribute schema uid, with one for each unresolved attribute
            of the object.

        Returns
        -------
        ObjectInMigration
            The object, with the resolved values and nothing unresolved.
        """
        resolved_mappings: list[
            dict[str, AnyAttribute | UnresolvedAttributeMigration]
        ] = []
        for attributes, schemas in (
            (object_.target_attributes, object_.target_schema.attributes),
            (
                object_.target_private_attributes,
                object_.target_schema.private_attributes,
            ),
        ):
            resolved_attributes: dict[
                str, AnyAttribute | UnresolvedAttributeMigration
            ] = {}
            for tag, attribute in attributes.items():
                if not isinstance(attribute, UnresolvedAttributeMigration):
                    resolved_attributes[tag] = attribute
                    continue
                # The planner refuses an unresolved attribute off the target
                # schema, so its tag has an attribute schema.
                resolved = resolutions[(object_.source.uid, schemas[tag].uid)].resolved
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
        self, session: Session, object_: ObjectInMigration
    ) -> DatabaseProject | DatabaseDataset | DatabaseItem:
        """Put an object on its target schema, and replace its attributes with
        the target ones.

        The old attributes are deleted and the target attributes inserted,
        keeping their uids, and with them the locks and read only flags of the
        old attributes of the same uid. The only rows referring to attributes
        are unmapped values, which go with them and are recorded again for the
        new attributes.

        Parameters
        ----------
        session: Session
            The session to write the object in.
        object_: ObjectInMigration
            The object, with the resolved values and nothing unresolved.

        Returns
        -------
        DatabaseProject | DatabaseDataset | DatabaseItem
            The object, written.

        Raises
        ------
        MigrationError
            If an attribute is not on the attribute schema of its tag.
        """
        database_object = self._get_database_object(session, object_.source)
        target_schema = object_.target_schema
        old_database_attributes: list[DatabaseAttribute] = [
            *database_object.attributes,
            *database_object.private_attributes,
        ]
        flags = {
            old.uid: (old.read_only, old.locked) for old in old_database_attributes
        }
        if old_database_attributes:
            # Deleted with them by the database, but said here for a database
            # that does not enforce its foreign keys.
            self._database_service.delete_unmapped_values(session, list(flags))
        database_object.attributes = set()
        database_object.private_attributes = set()
        session.flush()
        database_object.schema_uid = target_schema.uid
        database_object.attributes = self._add_attributes(
            session,
            database_object,
            object_.migrated_attributes,
            target_schema.attributes,
            flags,
        )
        database_object.private_attributes = self._add_attributes(
            session,
            database_object,
            object_.migrated_private_attributes,
            target_schema.private_attributes,
            flags,
        )
        return database_object

    def _get_database_object(
        self, session: Session, source: Project | Dataset | Item
    ) -> DatabaseProject | DatabaseDataset | DatabaseItem:
        """Get the database object of a project, dataset, or item.

        Parameters
        ----------
        session: Session
            The session to get it in.
        source: Project | Dataset | Item
            The object.

        Returns
        -------
        DatabaseProject | DatabaseDataset | DatabaseItem
            The database object.
        """
        if isinstance(source, Project):
            return self._database_service.get_project(session, source)
        if isinstance(source, Dataset):
            return self._database_service.get_dataset(session, source)
        return self._database_service.get_item(session, source)

    def _add_attributes(
        self,
        session: Session,
        database_object: DatabaseProject | DatabaseDataset | DatabaseItem,
        attributes: Mapping[str, AnyAttribute],
        schemas: Mapping[str, AttributeSchema],
        flags: Mapping[UUID, tuple[bool, bool]],
    ) -> set[DatabaseAttribute]:
        """Add the target attributes of an object.

        Parameters
        ----------
        session: Session
            The session to add them in.
        database_object: DatabaseProject | DatabaseDataset | DatabaseItem
            The object.
        attributes: Mapping[str, AnyAttribute]
            The target attributes, by tag.
        schemas: Mapping[str, AttributeSchema]
            The attribute schemas of the target schema, by tag.
        flags: Mapping[UUID, tuple[bool, bool]]
            The read only and locked flags of the old attributes, by uid.

        Returns
        -------
        set[DatabaseAttribute]
            The added attributes.

        Raises
        ------
        MigrationError
            If an attribute is not on the attribute schema of its tag.
        """
        database_attributes: set[DatabaseAttribute] = set()
        for tag, attribute in attributes.items():
            schema = RootSchemaIndex.refuse_attribute_off_schema(
                database_object.uid, tag, attribute, schemas.get(tag)
            )
            # Mapping items a mapper move removed are referred to by nothing.
            attribute = attribute.without_mapping_items(
                lambda uid: (
                    self._database_service.get_optional_mapping(session, uid) is None
                )
            )
            self._attribute_service.set_display_value(attribute)
            database_attribute = self._database_service.add_attribute(
                session, attribute, schema
            )
            database_attribute.rejected = attribute.rejected
            database_attribute.read_only, database_attribute.locked = flags.get(
                attribute.uid, (False, False)
            )
            database_attributes.add(database_attribute)
        return database_attributes
