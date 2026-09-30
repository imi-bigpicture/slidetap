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

"""What can be done with one project."""

from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cached_property
from typing import ClassVar
from uuid import UUID

from slidetap.model.batch_status import BatchStatus
from slidetap.model.errors import NotAllowedActionError, ProjectNotEditableError
from slidetap.model.image_status import ImageStatus
from slidetap.model.project_actions import ProjectActions
from slidetap.model.project_status import ProjectStatus


@dataclass(frozen=True)
class BatchActivity:
    """What the batches of a project are doing that rules migrating it out, by
    batch name."""

    busy: tuple[str, ...] = ()
    """Batches a task may be writing to: being searched or processed, with
    search items not yet searched, or with images being downloaded, processed,
    or stored."""

    stored: tuple[str, ...] = ()
    """Batches whose images are stored, with metadata written from the schema
    of the project, or locked to be. A batch whose images are processed but
    not stored is not: what is written into them is written when they are."""


@dataclass(frozen=True)
class RootSchemaSupport:
    """What the implementation allows to be done with a project under its root
    schema: changed, where the root is editable and the project's status does
    not rule it out, or else only viewed.
    """

    root_schema_uid: UUID
    """The uid of the root the project is on, or would be, for a new one."""

    root_name: str
    """The display name of the root, for what is refused."""

    editable: bool
    """Whether the projects on the root can be changed, with everything the
    application offers: editing, search, images, pseudonyms, preview, and
    export. Only those on the root of new projects can: the projects on a
    previous root are view only."""

    status: ProjectStatus

    exported: bool = False
    """Whether an export of the project has ever completed, whatever its
    status says now."""

    has_migration: bool = False
    """Whether a schema migration moves the projects on its root."""

    activity: Callable[[], BatchActivity] | None = field(
        default=None, compare=False, repr=False
    )
    """Reads what the batches of the project are doing, which is only read
    where it is asked for: whether the project can be migrated."""

    INACTIVE_STATUSES: ClassVar[dict[ProjectStatus, str]] = {
        ProjectStatus.DELETED: "the project is deleted",
        ProjectStatus.MIGRATING: "the project is being migrated",
    }
    """The statuses where nothing is done with a project, and why."""

    EXPORTED_STATUSES: ClassVar[frozenset[ProjectStatus]] = frozenset(
        {ProjectStatus.EXPORTING, ProjectStatus.EXPORT_COMPLETE}
    )
    """The statuses of a project that was exported, or is being."""

    BUSY_BATCH_STATUSES: ClassVar[frozenset[BatchStatus]] = frozenset(
        {
            BatchStatus.METADATA_SEARCHING,
            BatchStatus.IMAGE_PRE_PROCESSING,
            BatchStatus.IMAGE_POST_PROCESSING,
            BatchStatus.IMAGE_STORING,
        }
    )
    """Batch statuses where a task may be writing to the items."""

    IN_FLIGHT_IMAGE_STATUSES: ClassVar[frozenset[ImageStatus]] = frozenset(
        {
            ImageStatus.DOWNLOADING,
            ImageStatus.PRE_PROCESSING,
            ImageStatus.POST_PROCESSING,
            ImageStatus.STORING,
        }
    )
    """Image statuses where a task is working on the image."""

    STORED_BATCH_STATUSES: ClassVar[frozenset[BatchStatus]] = frozenset(
        {BatchStatus.LOCKED, BatchStatus.COMPLETED}
    )
    """Batch statuses where the images are stored, or locked to be: a locked
    batch holds what goes into its bundle, and is reopened to be changed."""

    @cached_property
    def batch_activity(self) -> BatchActivity:
        """What the batches of the project are doing."""
        return self.activity() if self.activity is not None else BatchActivity()

    @property
    def was_exported(self) -> bool:
        """Whether the project was ever exported, or is being."""
        return self.exported or self.status in self.EXPORTED_STATUSES

    @property
    def remappable(self) -> bool:
        """Whether what the project was mapped to follows a mapping that
        changes: not where it cannot be edited, nor where it was exported,
        which keeps what went out as it was."""
        return self.can_change and not self.was_exported

    @property
    def change_refusal(self) -> str | None:
        """Why the project cannot be changed, or None where it can.

        A change is everything but viewing the project, the results of
        validating it, and deleting it: editing, search, images, pseudonyms,
        preview, and export.
        """
        inactive = self.INACTIVE_STATUSES.get(self.status)
        if inactive is not None:
            return inactive
        if not self.editable:
            return f"{self.root_name} is view only"
        return None

    @property
    def can_change(self) -> bool:
        """Whether the project can be changed."""
        return self.change_refusal is None

    def assert_can_change(self) -> None:
        """Refuse a change to a project that cannot be changed.

        Raises
        ------
        ProjectNotEditableError
            If the project cannot be changed, with why.
        """
        reason = self.change_refusal
        if reason is not None:
            raise ProjectNotEditableError(self.root_schema_uid, reason)

    def migrate_refusal(self, started: bool = False) -> str | None:
        """Why the project cannot be migrated, or None where it can.

        Only a project that was never exported is: what was exported is out
        there on the schema it was exported with, which the project keeps.

        Parameters
        ----------
        started: bool = False
            Whether the migration is under way, the project set as migrating
            for it, which is then what it has to be.
        """
        if not self.has_migration:
            return "its root has no migration"
        if started:
            if self.status != ProjectStatus.MIGRATING:
                return "it is not being migrated"
        elif self.status in self.INACTIVE_STATUSES:
            return self.INACTIVE_STATUSES[self.status]
        if self.was_exported:
            return "it was exported, and keeps the schema it was exported with"
        activity = self.batch_activity
        if activity.stored:
            return (
                f"the images of batches {', '.join(activity.stored)} are stored, "
                f"or locked to be, with the metadata of its schema"
            )
        if activity.busy:
            return f"batches {', '.join(activity.busy)} are being searched or processed"
        return None

    @property
    def can_migrate(self) -> bool:
        """Whether the project can be migrated now."""
        return self.migrate_refusal() is None

    def assert_can_migrate(self, started: bool = False) -> None:
        """Refuse migrating a project that cannot be, see `migrate_refusal`.

        Raises
        ------
        NotAllowedActionError
            If the project cannot be migrated, with why.
        """
        reason = self.migrate_refusal(started)
        if reason is not None:
            raise NotAllowedActionError(f"The project cannot be migrated: {reason}.")

    @staticmethod
    def assert_can_delete(status: ProjectStatus) -> None:
        """Refuse deleting a project a migration may be writing to.

        By its status alone, as a project on a root the application no longer
        provides is deleted too.

        Raises
        ------
        NotAllowedActionError
            If the project is being migrated.
        """
        if status == ProjectStatus.MIGRATING:
            raise NotAllowedActionError(
                "The project cannot be deleted: the project is being migrated."
            )

    @property
    def actions(self) -> ProjectActions:
        """What the project is offered."""
        return ProjectActions(edit=self.can_change)
