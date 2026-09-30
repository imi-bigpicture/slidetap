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

"""What can be done with a project, given the root schema it is on."""

from slidetap.model.base_model import CamelCaseBaseModel


class ProjectActions(CamelCaseBaseModel):
    """What a project can be offered.

    Viewing a project, the results of validating it, and deleting it are
    offered for every project. A project that cannot be edited is view only.
    """

    edit: bool
    """Every change to the project: editing, search, images, pseudonyms,
    preview, and export."""

    migrate: bool = False
    """Moving the project to another root schema of its family: offered where
    a schema migration exists for the root, and the project's state allows
    it, whether or not the project can be changed."""

    has_migration: bool = False
    """Whether a schema migration moves the projects on its root, whether or
    not this project can be moved now."""

    migrate_refusal: str | None = None
    """Why the project cannot be migrated, where its root has a migration."""
