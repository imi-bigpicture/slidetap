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

from dataclasses import dataclass
from typing import ClassVar
from uuid import UUID

from slidetap.model.errors import ProjectNotEditableError
from slidetap.model.project_actions import ProjectActions
from slidetap.model.project_status import ProjectStatus


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

    INACTIVE_STATUSES: ClassVar[dict[ProjectStatus, str]] = {
        ProjectStatus.DELETED: "the project is deleted",
    }
    """The statuses where nothing is done with a project, and why."""

    EXPORTED_STATUSES: ClassVar[frozenset[ProjectStatus]] = frozenset(
        {ProjectStatus.EXPORTING, ProjectStatus.EXPORT_COMPLETE}
    )
    """The statuses of a project that was exported, or is being."""

    @property
    def was_exported(self) -> bool:
        """Whether the project was exported, or is being."""
        return self.status in self.EXPORTED_STATUSES

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

    @property
    def actions(self) -> ProjectActions:
        """What the project is offered."""
        return ProjectActions(edit=self.can_change)
