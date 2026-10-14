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

"""Errors for what is refused, raised by models and services."""

from uuid import UUID


class NotAllowedActionError(Exception):
    """Raised when action on item in database is not allowed."""

    def __init__(self, error: str):
        self.error = error

    def __str__(self) -> str:
        return self.error


class NotFoundError(Exception):
    """Raised when item in database is not found."""

    def __init__(self, error: str):
        self.error = error

    def __str__(self) -> str:
        return self.error


class ProjectNotEditableError(NotAllowedActionError):
    """Raised for a change to a project that cannot be changed: one on a view
    only root, or one whose state rules it out, which the reason says."""

    def __init__(self, root_schema_uid: UUID, reason: str):
        self.root_schema_uid = root_schema_uid
        self.reason = reason
        super().__init__(f"The project cannot be changed: {reason}.")


class MigrationError(Exception):
    """Raised where a migration returns what it may not.

    Nothing of the project is changed: a migration is applied in one
    transaction, and this fails it.
    """
