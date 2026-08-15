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

"""What a MetadataImportInterface leaves for a later step to fill in."""

from uuid import UUID

from pydantic import Field

from slidetap.model.base_model import FrozenBaseModel


class MetadataImportCompleteness(FrozenBaseModel):
    """What a MetadataImportInterface does not include in the MetadataSearchResult.

    A MetadataImportInterface need not produce a complete hierarchy: items may be
    missing, and produced items may be missing attributes.
    """

    non_complete_items: frozenset[UUID] = Field(default_factory=frozenset)
    """Items whose attributes are not included in the MetadataSearchResult, by item
    schema uid.

    Only the attributes are missing. Their relations and pseudonym are included, and
    a relation of theirs is missing only if it is also named in
    non_complete_relations.
    """

    non_complete_relations: frozenset[UUID] = Field(default_factory=frozenset)
    """Relations that are not satisfied in the MetadataSearchResult, by relation uid.

    Only the named relations are missing. Every other relation is satisfied, also for
    items named in non_complete_items.
    """
