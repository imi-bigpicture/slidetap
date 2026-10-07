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

    has_migration: bool
    """Whether the projects on the project's root can be converted to the root
    of new projects."""

    migrate_refusal: str | None
    """Why the project cannot be converted now, None where it can or where its
    root has no migration."""
