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

"""How far a step of planning or completing a migration has come."""

import time
from collections.abc import Callable
from typing import ClassVar
from uuid import UUID

from slidetap.model import MigrationProgress, MigrationStep
from slidetap.services.database_service import DatabaseService


class MigrationProgressReporter:
    """Counts the entities a step of planning or completing a migration is
    done with, and writes how far it has come for the client to show.

    Written when the step starts, when it is done, and in between at most once
    every `INTERVAL` seconds, as each write is a transaction of its own.
    """

    INTERVAL: ClassVar[float] = 1.0
    """The least time, in seconds, between two writes within a step."""

    def __init__(
        self,
        database_service: DatabaseService,
        migration_uid: UUID,
        step: MigrationStep,
        total: int,
        clock: Callable[[], float] = time.monotonic,
    ):
        """Start a step, writing that none of it is done.

        Parameters
        ----------
        database_service: DatabaseService
            For writing the progress.
        migration_uid: UUID
            The uid of the migration.
        step: MigrationStep
            The step.
        total: int
            How many entities the step has.
        clock: Callable[[], float] = time.monotonic
            The time in seconds, for when to write next.
        """
        self._database_service = database_service
        self._migration_uid = migration_uid
        self._step = step
        self._total = total
        self._clock = clock
        self._done = 0
        self._written_at = clock()
        self._write()

    @property
    def done(self) -> int:
        """How many entities of the step are done."""
        return self._done

    @property
    def total(self) -> int:
        """How many entities the step has."""
        return self._total

    def advance(self, count: int = 1) -> None:
        """Count entities as done, and write the progress where the step is
        done or it was last written long enough ago.

        Parameters
        ----------
        count: int = 1
            How many more entities are done.
        """
        self._done = min(self._done + count, self._total)
        now = self._clock()
        if self._done == self._total or now - self._written_at >= self.INTERVAL:
            self._written_at = now
            self._write()

    def _write(self) -> None:
        self._database_service.set_project_migration_progress(
            self._migration_uid,
            MigrationProgress(step=self._step, done=self._done, total=self._total),
        )
