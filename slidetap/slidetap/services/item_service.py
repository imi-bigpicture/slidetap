"""Service for accessing attributes."""
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Union
from uuid import UUID

from slidetap.database import Annotation, Image, Item, ItemSchema, Observation, Sample
from slidetap.database.project import Project
from slidetap.database.schema.item_schema import (
    AnnotationSchema,
    ImageSchema,
    ObservationSchema,
    SampleSchema,
)
from slidetap.exporter.metadata.metadata_exporter import MetadataExporter
from slidetap.model import ItemValueType
from slidetap.model.table import ColumnSort
from slidetap.services.attribute_service import AttributeService


class ItemService:
    """Item service should be used to interface with items"""

    def __init__(self, metadata_exporter: MetadataExporter) -> None:
        self.attribute_service = AttributeService()
        self.metadata_exporter = metadata_exporter

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

    def create(
        self, item_schema: Union[UUID, ItemSchema], project_uid: UUID
    ) -> Optional[Item]:
        if not isinstance(item_schema, ItemSchema):
            fetched_item_schema = ItemSchema.get_by_uid(item_schema)
            if fetched_item_schema is None:
                return None
            item_schema = fetched_item_schema
        project = Project.get(project_uid)
        if project is None:
            return None
        empty_attributes = [
            self.attribute_service.create(attribute, None)
            for attribute in item_schema.attributes
        ]
        if isinstance(item_schema, SampleSchema):
            return Sample(
                project,
                item_schema,
                "New sample",
                [],
                empty_attributes,
                add=False,
                commit=False,
            )
        if isinstance(item_schema, ImageSchema):
            return Image(
                project,
                item_schema,
                "New image",
                [],
                empty_attributes,
                add=False,
                commit=False,
            )
        if isinstance(item_schema, AnnotationSchema):
            return Annotation(
                project,
                item_schema,
                "New annotation",
                None,
                empty_attributes,
                add=False,
                commit=False,
            )
        if isinstance(item_schema, ObservationSchema):
            return Observation(
                project,
                item_schema,
                "New observation",
                None,
                empty_attributes,
                add=False,
                commit=False,
            )

    def get_for_schema(
        self,
        item_schema_uid: UUID,
        project_uid: UUID,
        start: Optional[int] = None,
        size: Optional[int] = None,
        identifier_filter: Optional[str] = None,
        attribute_filters: Optional[Dict[str, str]] = None,
        sorting: Optional[Iterable[ColumnSort]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> Sequence[Item]:
        item_schema = ItemSchema.get_by_uid(item_schema_uid)
        if isinstance(item_schema, SampleSchema):
            sample_class = Sample
        elif isinstance(item_schema, ImageSchema):
            sample_class = Image
        elif isinstance(item_schema, AnnotationSchema):
            sample_class = Annotation
        elif isinstance(item_schema, ObservationSchema):
            sample_class = Observation
        else:
            raise TypeError(f"Unknown item type {item_schema}.")

        return sample_class.get_for_project(
            project_uid,
            item_schema,
            start,
            size,
            identifier_filter,
            attribute_filters,
            sorting,
            selected,
            valid,
        )

    def get_count_for_schema(
        self,
        item_schema_uid: UUID,
        project_uid: UUID,
        identifier_filter: Optional[str] = None,
        attribute_filters: Optional[Dict[str, str]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> int:
        return Item.get_count_for_project(
            project_uid,
            item_schema_uid,
            identifier_filter,
            attribute_filters,
            selected=selected,
            valid=valid,
        )

    def get_preview(self, item_uid: UUID) -> Optional[str]:
        item = Item.get_optional(item_uid)
        if item is None:
            return None
        return self.metadata_exporter.preview_item(item)
