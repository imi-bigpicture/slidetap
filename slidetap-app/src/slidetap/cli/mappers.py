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

"""Commands that set up the stored mappers of an application.

``slidetap-mappers set-up`` is a deploy step, run after ``slidetap-db upgrade``.
It gives the stored mappers their family, migrates the mappers whose attributes
the schema migrations move, and injects the mapper sheets of the plugin, in
that order: a mapper sheet of the root migrated to finds the mapper it names
migrated there already, with its mapping items migrated.

The container is created by ``create_container()`` in the ``container`` module
of the application's package, which ``SLIDETAP_TASK_APP`` names as it does for
``slidetap-task-worker``. The database is given by ``--db-uri`` or, if that is
omitted, by the ``SLIDETAP_DBURI`` environment variable, which is where the
container reads it from.
"""

import importlib
import logging
import os

import typer
from dishka import Container

from slidetap.migrations.cli import DbUri
from slidetap.services import MapperService, MigrationService

app = typer.Typer(
    help="Set up the stored mappers of a SlideTap application.",
    no_args_is_help=True,
)


class MapperSetUp:
    """Set up the stored mappers with the services of an application."""

    def __init__(
        self, mapper_service: MapperService, migration_service: MigrationService
    ):
        """Create the set-up.

        Parameters
        ----------
        mapper_service: MapperService
            For giving the mappers their family and injecting the plugin's.
        migration_service: MigrationService
            For migrating the mappers the schema migrations move.
        """
        self._mapper_service = mapper_service
        self._migration_service = migration_service

    @classmethod
    def from_container(cls, container: Container) -> "MapperSetUp":
        """Create the set-up with the services of a container.

        Parameters
        ----------
        container: Container
            The container of the application.

        Returns
        -------
        MapperSetUp
            The set-up.
        """
        return cls(container.get(MapperService), container.get(MigrationService))

    def run(self) -> None:
        """Give the stored mappers their family, migrate the mappers the schema
        migrations move, and inject the mapper sheets of the plugin.

        Raises
        ------
        ValueError
            If a migration fails on the attributes of a mapper, naming it.
        """
        self._mapper_service.assign_families()
        self._migration_service.migrate_mappers()
        self._mapper_service.inject_mappers()


@app.callback()
def main() -> None:
    """Set up the stored mappers of a SlideTap application."""


@app.command()
def set_up(db_uri: DbUri = "") -> None:
    """Set up the stored mappers of the application named by SLIDETAP_TASK_APP.

    Give the stored mappers their family, migrate the mappers the schema
    migrations move, and inject the mapper sheets of the plugin. Run after
    `slidetap-db upgrade`, on every deploy; running it again changes nothing
    that has not changed since.
    """
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)-5.5s [%(name)s] %(message)s"
    )
    if db_uri:
        # The container reads the database URL from the environment.
        os.environ["SLIDETAP_DBURI"] = db_uri
    module = importlib.import_module(f"{os.environ['SLIDETAP_TASK_APP']}.container")
    container: Container = module.create_container()
    try:
        MapperSetUp.from_container(container).run()
    finally:
        container.close()
    print("Mappers set up.")
