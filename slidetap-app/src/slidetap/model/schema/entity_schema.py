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

"""The schema of an entity: a project, a dataset, or an item."""

from slidetap.model.schema.dataset_schema import DatasetSchema
from slidetap.model.schema.item_schema import ItemSchema
from slidetap.model.schema.project_schema import ProjectSchema

AnyEntitySchema = ProjectSchema | DatasetSchema | ItemSchema
"""The schema of a project, a dataset, or an item."""
