"""Service for accessing attributes."""
from typing import Any, List, Mapping, Optional, Sequence
from uuid import UUID

from slidetap.database import Annotation, Image, Item, ItemSchema, Observation, Sample
from slidetap.database.project import Project
from slidetap.database.schema.item_schema import (
    AnnotationSchema,
    ImageSchema,
    ObservationSchema,
    SampleSchema,
)
from slidetap.model import ItemValueType
from slidetap.services.attribute_service import AttributeService


class ItemService:
    """Item service should be used to interface with items"""

    attribute_service = AttributeService()

    def get(self, item_uid: UUID) -> Optional[Item]:
        return Item.get_optional(item_uid)

    def select(self, item_uid: UUID, value: bool) -> Optional[Item]:
        item = Item.get_optional(item_uid)
        if item is None:
            return None
        item.set_select(value)
        return item

    def get_schema_for_item(self, item_uid: UUID) -> Optional[ItemSchema]:
        item = Item.get_optional(item_uid)
        if item is None:
            return None
        return item.schema

    def update(self, item_data: Mapping[str, Any]) -> Optional[Item]:
        item_value_type = item_data["item_value_type"]
        item_uid = item_data["uid"]
        assert isinstance(item_value_type, ItemValueType)
        if item_value_type == ItemValueType.SAMPLE:
            item = Sample.get(item_uid)
            if item is None:
                return None
            item.set_parents(
                Sample.get(parent["uid"]) for parent in item_data["parents"]
            )
            item.set_children(
                Sample.get(child["uid"]) for child in item_data["children"]
            )
        elif item_value_type == ItemValueType.IMAGE:
            item = Image.get_optional(item_uid)
            if item is None:
                return None
            item.set_samples(
                Sample.get(sample["uid"]) for sample in item_data["samples"]
            )
        elif item_value_type == ItemValueType.ANNOTATION:
            item = Annotation.get_optional(item_uid)
            if item is None:
                return None
            image = Image.get(item_data["image"]["uid"])
            if image is None:
                raise ValueError(f"Image {item_data['image']['uid']} not found.")
            item.image = image
        elif item_value_type == ItemValueType.OBSERVATION:
            item = Observation.get_optional(item_uid)
            if item is None:
                return None
            observerd_on_item = Item.get_optional(item_data["observed_on"]["uid"])
            if not isinstance(observerd_on_item, (Image, Sample, Annotation)):
                raise ValueError(f"Item {item_data['observed_on']['uid']} not found.")
            item.set_item(observerd_on_item)
        else:
            raise TypeError(f"Unknown item type {item_value_type}.")

    def add(self, item: Item):
        Item.add(item)

    def copy(self, item_uid: UUID) -> Optional[Item]:
        item = Item.get_optional(item_uid)
        if item is None:
            return None
        return item.copy()

    def create(self, item_schema_uid: UUID, project_uid: UUID) -> Optional[Item]:
        item_schema = ItemSchema.get_by_uid(item_schema_uid)
        if item_schema is None:
            return None
        project = Project.get_project(project_uid)
        if project is None:
            return None
        empty_attributes = [
            self.attribute_service.create(attribute, None)
            for attribute in item_schema.attributes
        ]
        if isinstance(item_schema, SampleSchema):
            return Sample(
                project,
                "New sample",
                item_schema,
                [],
                empty_attributes,
                False,
                False,
            )
        if isinstance(item_schema, ImageSchema):
            return Image(
                project, "New image", item_schema, [], empty_attributes, False, False
            )
        if isinstance(item_schema, AnnotationSchema):
            return Annotation(
                project,
                "New annotation",
                item_schema,
                None,
                empty_attributes,
                False,
                False,
            )
        if isinstance(item_schema, ObservationSchema):
            return Observation(
                project,
                "New observation",
                item_schema,
                None,
                empty_attributes,
                False,
                False,
            )

    def get_of_schema(self, item_schema_uid: UUID, project_uid: UUID) -> Sequence[Item]:
        return Item.get_for_project(project_uid, item_schema_uid, True)
