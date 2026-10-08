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

"""Moving the stored mappers to the schemas the schema migrations give their
attributes."""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from slidetap.database import DatabaseMapper
from slidetap.external_interfaces import SchemaMigration
from slidetap.services.database_service import DatabaseService
from slidetap.services.mapper_service import MapperService
from slidetap.services.schema_service import SchemaService


class MapperMigrationService:
    """Moves the stored mappers to the schemas the schema migrations give
    their attributes, with their mapping items migrated."""

    def __init__(
        self,
        schema_service: SchemaService,
        database_service: DatabaseService,
        mapper_service: MapperService,
    ):
        """Create the mapper migration service.

        Parameters
        ----------
        schema_service: SchemaService
            For the roots and their migrations.
        database_service: DatabaseService
            For the sessions and the rows of the mappers.
        mapper_service: MapperService
            For removing the mapping items a migration leaves without a target.
        """
        self._schema_service = schema_service
        self._database_service = database_service
        self._mapper_service = mapper_service
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def migrate_mappers(self) -> None:
        """Migrate the mappers of the attributes that a schema migration gives
        another schema.

        Migrations are to the root of new projects only, so a mapper is
        migrated once at most, and running this again changes nothing.

        Raises
        ------
        ValueError
            If a migration fails on the attributes of a mapper, naming it.
        """
        migrations = self._schema_service.migrations
        with self._database_service.get_session() as session:
            for mapper in self._database_service.get_all_mappers(session):
                for source_uid, migration in migrations.items():
                    source = self._schema_service.get_root(source_uid)
                    if not source.has_attribute(mapper.attribute_schema_uid):
                        continue
                    try:
                        migrated = self._migrate_mapper(session, migration, mapper)
                    except Exception as exception:
                        raise ValueError(
                            f"Mapper '{mapper.name}' could not be migrated from "
                            f"root schema {source_uid} to "
                            f"{self._schema_service.default_root.uid}: {exception}"
                        ) from exception
                    if migrated:
                        break

    def _migrate_mapper(
        self, session: Session, migration: SchemaMigration, mapper: DatabaseMapper
    ) -> bool:
        """Migrate a mapper to the schemas a migration gives its attributes, and
        to the family of the root of new projects.

        The schemas are given by `SchemaMigration.migrate_attribute_schema`
        for the attribute schema of the mapper and its root attribute schema;
        a mapper whose schemas the migration gives no target, or the same ones,
        is left as it is. The mapper keeps its uid, name, groups, expressions,
        and hits, and each of its mapping items is migrated in place by
        `migrate_attribute`. A mapping item migrated to None, or to an
        attribute without an original value, is removed, and the attributes it
        mapped keep what they were mapped to.

        Parameters
        ----------
        session: Session
            The session to migrate it in.
        migration: SchemaMigration
            The migration from the root of the mapper.
        mapper: DatabaseMapper
            The mapper.

        Returns
        -------
        bool
            Whether the mapper was migrated.

        Raises
        ------
        ValueError
            If another mapper of its name is in the family it is migrated to.
        """
        try:
            attribute_schema = self._schema_service.get_any_attribute(
                mapper.attribute_schema_uid
            )
            root_attribute_schema = self._schema_service.get_any_attribute(
                mapper.root_attribute_schema_uid
            )
        except ValueError:
            return False
        target_attribute_schema = migration.migrate_attribute_schema(attribute_schema)
        target_root_attribute_schema = (
            target_attribute_schema
            if root_attribute_schema.uid == attribute_schema.uid
            else migration.migrate_attribute_schema(root_attribute_schema)
        )
        if target_attribute_schema is None or target_root_attribute_schema is None:
            return False
        if (target_attribute_schema.uid, target_root_attribute_schema.uid) == (
            mapper.attribute_schema_uid,
            mapper.root_attribute_schema_uid,
        ):
            # The same schema in both roots, which the mapper serves as it is.
            return False
        if self._database_service.get_mapper_for_schemas(
            session, target_attribute_schema.uid, target_root_attribute_schema.uid
        ):
            self._logger.warning(
                f"Mapper {mapper.name} is not migrated to attribute schema "
                f"{target_attribute_schema.uid}, which another mapper maps."
            )
            return False
        family_uid = self._schema_service.default_root.family_uid
        named = self._database_service.get_mapper_by_name(
            session, mapper.name, family_uid
        )
        if named is not None and named.uid != mapper.uid:
            raise ValueError(
                f"Mapper '{mapper.name}' cannot be migrated to family {family_uid}, "
                f"which has another mapper of that name."
            )
        removed: set[UUID] = set()
        for mapping in list(
            self._database_service.get_mappings_for_mapper(session, mapper.uid)
        ):
            attribute = migration.migrate_attribute(mapping.attribute)
            # A mapping maps to what its attribute was imported with, and one
            # whose value has no counterpart would map to nothing.
            if attribute is None or attribute.original_value is None:
                self._logger.warning(
                    f"Mapping {mapping.expression!r} of mapper {mapper.name} has no "
                    f"target, and is removed."
                )
                removed.add(mapping.uid)
                continue
            mapping.attribute = attribute
        if removed:
            self._mapper_service.forget_mapping_items(
                session, mapper.root_attribute_schema_uid, removed
            )
        mapper.attribute_schema_uid = target_attribute_schema.uid
        mapper.root_attribute_schema_uid = target_root_attribute_schema.uid
        mapper.family_uid = family_uid
        session.flush()
        self._logger.info(
            f"Moved mapper {mapper.name} to attribute schema "
            f"{target_attribute_schema.uid}."
        )
        return True
