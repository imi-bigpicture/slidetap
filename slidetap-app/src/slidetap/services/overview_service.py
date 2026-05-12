#    Copyright 2024 SECTRA AB
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

"""Service for building parent-rooted overview views from a layout."""

import logging
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from slidetap.database import DatabaseSample
from slidetap.model import (
    AnyAttribute,
    Item,
    ObservationSchema,
    OverviewLayout,
    OverviewSectionLayout,
    SampleSchema,
)
from slidetap.model.overview import (
    OverviewItem,
    OverviewRoot,
    OverviewSection,
)
from slidetap.services.attribute_service import AttributeService
from slidetap.services.database_service import DatabaseService
from slidetap.services.schema_service import SchemaService


class OverviewService:
    """Build the parent-rooted overview view consumed by the overview page."""

    def __init__(
        self,
        attribute_service: AttributeService,
        schema_service: SchemaService,
        database_service: DatabaseService,
    ) -> None:
        self._attribute_service = attribute_service
        self._schema_service = schema_service
        self._database_service = database_service
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def get_overview_data(
        self,
        item_uid: UUID,
        overview_layout: OverviewLayout,
        pseudonym_mode: bool = False,
    ) -> Optional[OverviewRoot]:
        with self._database_service.get_session() as session:
            parent = self._database_service.get_optional_item(session, item_uid)
            if parent is None:
                return None
            if not isinstance(parent, DatabaseSample):
                raise ValueError(
                    f"Overview is only supported for sample items, "
                    f"got {type(parent).__name__} for item {item_uid}"
                )

            # Build sections from layout
            sections: List[OverviewSection] = []

            for section in overview_layout.sections:
                target_schema = self._schema_service.items.get(section.schema_uid)
                if target_schema is None:
                    self._logger.warning(
                        f"Section target schema {section.schema_uid} "
                        f"not found, skipping"
                    )
                    continue

                # If target is the parent itself, show parent's attributes
                if section.schema_uid == parent.schema_uid:
                    attrs, private_attrs = self._collect_section_attributes(
                        parent.model, section
                    )
                    sections.append(
                        OverviewSection(
                            item_uid=parent.uid,
                            label=(section.display_name or parent.identifier),
                            pseudonym=(
                                None if section.display_name else parent.pseudonym
                            ),
                            schema_uid=section.schema_uid,
                            items=[
                                OverviewItem(
                                    item_uid=parent.uid,
                                    identifier=parent.identifier,
                                    pseudonym=parent.pseudonym,
                                    attributes=attrs,
                                    private_attributes=private_attrs,
                                )
                            ],
                        )
                    )
                    continue

                # Traverse the path from root to find parent items.
                # Filter by selected so deselected/recycled specimens don't
                # surface as parents in the overview.
                if not section.path:
                    # No path = parent is the root itself
                    group_items = [parent]
                else:
                    # Walk path step by step to reach parent items
                    current_items: List[DatabaseSample] = [parent]
                    for step_schema_uid in section.path:
                        next_items: List[DatabaseSample] = []
                        for item in current_items:
                            next_items.extend(
                                self._database_service.get_sample_children(
                                    session,
                                    item,
                                    step_schema_uid,
                                    selected=True,
                                )
                            )
                        current_items = next_items
                    group_items = sorted(current_items, key=lambda c: c.identifier)

                for group_child in group_items:
                    target_items: List[OverviewItem] = []

                    if isinstance(target_schema, ObservationSchema):
                        for observation in group_child.observations:
                            if observation.schema_uid != section.schema_uid:
                                continue
                            if not observation.selected:
                                continue
                            obs_model = observation.model
                            attrs, private_attrs = self._collect_section_attributes(
                                obs_model, section
                            )
                            target_items.append(
                                OverviewItem(
                                    item_uid=observation.uid,
                                    identifier=observation.identifier,
                                    pseudonym=observation.pseudonym,
                                    attributes=attrs,
                                    private_attributes=private_attrs,
                                )
                            )
                    elif isinstance(target_schema, SampleSchema):
                        children = self._database_service.get_sample_children(
                            session,
                            group_child,
                            section.schema_uid,
                            recursive=True,
                            selected=True,
                        )
                        for child in sorted(children, key=lambda c: c.identifier):
                            child_model = child.model
                            attrs, private_attrs = self._collect_section_attributes(
                                child_model, section
                            )
                            target_items.append(
                                OverviewItem(
                                    item_uid=child.uid,
                                    identifier=child.identifier,
                                    pseudonym=child.pseudonym,
                                    attributes=attrs,
                                    private_attributes=private_attrs,
                                )
                            )
                    else:
                        self._logger.warning(
                            f"Unsupported target schema type "
                            f"{type(target_schema).__name__} in overview section"
                        )

                    if target_items or section.creatable:
                        use_section_label = section.display_name and not section.path
                        sections.append(
                            OverviewSection(
                                item_uid=group_child.uid,
                                label=(
                                    section.display_name
                                    if use_section_label
                                    else group_child.identifier
                                ),
                                pseudonym=(
                                    None
                                    if use_section_label
                                    else group_child.pseudonym
                                ),
                                schema_uid=section.schema_uid,
                                items=target_items,
                            )
                        )

            # Find previous/next sibling parent items. Skip deselected
            # siblings so navigation matches what's visible in the dataset.
            previous_uid = None
            next_uid = None
            parent_schema = self._schema_service.samples.get(parent.schema_uid)
            if parent_schema is not None:
                siblings = list(
                    self._database_service.get_samples(
                        session,
                        parent_schema,
                        parent.dataset_uid,
                        selected=True,
                    )
                )

                def _sort_key(s: DatabaseSample) -> str:
                    if not pseudonym_mode:
                        return s.identifier
                    if s.pseudonym:
                        return s.pseudonym
                    return f"ANON-{str(s.uid)[:8].upper()}"

                siblings.sort(key=_sort_key)
                for i, sibling in enumerate(siblings):
                    if sibling.uid == parent.uid:
                        if i > 0:
                            previous_uid = siblings[i - 1].uid
                        if i < len(siblings) - 1:
                            next_uid = siblings[i + 1].uid
                        break

            return OverviewRoot(
                item_uid=parent.uid,
                identifier=parent.identifier,
                pseudonym=parent.pseudonym,
                batch_uid=parent.batch_uid,
                sections=sections,
                previous_uid=previous_uid,
                next_uid=next_uid,
            )

    def _collect_section_attributes(
        self,
        item_model: Item,
        section: OverviewSectionLayout,
    ) -> Tuple[Dict[str, AnyAttribute], Dict[str, AnyAttribute]]:
        """Collect attributes and private attributes for a section.

        Returns a tuple of (attributes, private_attributes).
        """
        attributes: Dict[str, AnyAttribute] = {}
        if section.attributes:
            for tag in section.attributes:
                attr = self._attribute_service.resolve_attribute(
                    item_model.attributes, tag
                )
                if attr is not None:
                    attributes[tag] = attr
        else:
            attributes.update(item_model.attributes)

        private_attributes: Dict[str, AnyAttribute] = {}
        if section.private_attributes:
            for tag in section.private_attributes:
                attr = self._attribute_service.resolve_attribute(
                    item_model.private_attributes, tag
                )
                if attr is not None:
                    private_attributes[tag] = attr
        else:
            private_attributes.update(item_model.private_attributes)

        return attributes, private_attributes
