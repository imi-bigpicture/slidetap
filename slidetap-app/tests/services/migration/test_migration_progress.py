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

from typing import cast
from uuid import UUID, uuid4

import pytest

from slidetap.model import MigrationProgress, MigrationStep
from slidetap.services.database_service import DatabaseService
from slidetap.services.migration.migration_progress import MigrationProgressReporter


class RecordingDatabaseService:
    """Records the progress written, rather than writing it."""

    def __init__(self):
        self.written: list[tuple[UUID, MigrationProgress]] = []

    def set_project_migration_progress(
        self, migration_uid: UUID, progress: MigrationProgress
    ) -> None:
        self.written.append((migration_uid, progress))


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture()
def database_service() -> RecordingDatabaseService:
    return RecordingDatabaseService()


@pytest.fixture()
def clock() -> Clock:
    return Clock()


@pytest.fixture()
def migration_uid() -> UUID:
    return uuid4()


@pytest.fixture()
def reporter(
    database_service: RecordingDatabaseService, clock: Clock, migration_uid: UUID
) -> MigrationProgressReporter:
    return MigrationProgressReporter(
        cast(DatabaseService, database_service),
        migration_uid,
        MigrationStep.WRITING,
        10,
        clock,
    )


@pytest.mark.unittest
class TestMigrationProgressReporter:
    def test_starting_a_step_writes_that_none_of_it_is_done(
        self,
        reporter: MigrationProgressReporter,
        database_service: RecordingDatabaseService,
        migration_uid: UUID,
    ):
        # Assert
        assert database_service.written == [
            (
                migration_uid,
                MigrationProgress(step=MigrationStep.WRITING, done=0, total=10),
            )
        ]

    def test_progress_is_not_written_again_within_the_interval(
        self,
        reporter: MigrationProgressReporter,
        database_service: RecordingDatabaseService,
        clock: Clock,
    ):
        # Arrange
        clock.now = MigrationProgressReporter.INTERVAL / 2

        # Act
        reporter.advance(3)

        # Assert
        assert [progress.done for _, progress in database_service.written] == [0]
        assert reporter.done == 3

    def test_progress_is_written_once_the_interval_has_passed(
        self,
        reporter: MigrationProgressReporter,
        database_service: RecordingDatabaseService,
        clock: Clock,
    ):
        # Arrange
        reporter.advance(3)
        clock.now = MigrationProgressReporter.INTERVAL

        # Act
        reporter.advance(2)

        # Assert
        assert [progress.done for _, progress in database_service.written] == [0, 5]

    def test_the_end_of_a_step_is_written_whenever_it_comes(
        self,
        reporter: MigrationProgressReporter,
        database_service: RecordingDatabaseService,
    ):
        # Act
        reporter.advance(10)

        # Assert
        assert [progress.done for _, progress in database_service.written] == [0, 10]

    def test_more_done_than_the_step_has_is_counted_as_the_whole_step(
        self,
        reporter: MigrationProgressReporter,
        database_service: RecordingDatabaseService,
    ):
        # Act
        reporter.advance(12)

        # Assert
        assert reporter.done == 10
        assert database_service.written[-1][1].done == 10
