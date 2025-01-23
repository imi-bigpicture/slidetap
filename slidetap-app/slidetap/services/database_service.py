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

"""Service for accessing attributes."""
from typing import Dict, Iterable, Optional, Set, Union
from uuid import UUID

from slidetap.database import (
    DatabaseAnnotation,
    DatabaseAttribute,
    DatabaseBooleanAttribute,
    DatabaseCodeAttribute,
    DatabaseDatetimeAttribute,
    DatabaseEnumAttribute,
    DatabaseImage,
    DatabaseItem,
    DatabaseListAttribute,
    DatabaseMeasurementAttribute,
    DatabaseNumericAttribute,
    DatabaseObjectAttribute,
    DatabaseObservation,
    DatabaseProject,
    DatabaseSample,
    DatabaseStringAttribute,
    DatabaseUnionAttribute,
    db,
)
from slidetap.database.item import DatabaseImageFile
from slidetap.database.project import DatabaseBatch, DatabaseDataset
from slidetap.model import (
    Annotation,
    AnnotationSchema,
    Attribute,
    BooleanAttribute,
    BooleanAttributeSchema,
    CodeAttribute,
    CodeAttributeSchema,
    ColumnSort,
    DatetimeAttribute,
    DatetimeAttributeSchema,
    EnumAttribute,
    EnumAttributeSchema,
    Image,
    ImageSchema,
    Item,
    ItemSchema,
    ItemType,
    ListAttribute,
    ListAttributeSchema,
    MeasurementAttribute,
    MeasurementAttributeSchema,
    NumericAttribute,
    NumericAttributeSchema,
    ObjectAttribute,
    ObjectAttributeSchema,
    Observation,
    ObservationSchema,
    Project,
    Sample,
    SampleSchema,
    StringAttribute,
    StringAttributeSchema,
    UnionAttribute,
    UnionAttributeSchema,
)
from slidetap.model.batch import Batch
from slidetap.model.dataset import Dataset
from slidetap.model.image_status import ImageStatus
from slidetap.model.schema.attribute_schema import AttributeSchema
from sqlalchemy import Select, and_, func, select


class DatabaseService:
    def get_project(self, project: Union[UUID, Project, DatabaseProject]):
        if isinstance(project, UUID):
            return db.session.get_one(DatabaseProject, project)
        elif isinstance(project, Project):
            return db.session.get_one(DatabaseProject, project.uid)
        return project

    def get_optional_project(
        self, project: Union[UUID, Project, DatabaseProject]
    ) -> Optional[DatabaseProject]:
        if isinstance(project, UUID):
            return db.session.get(DatabaseProject, project)
        elif isinstance(project, Project):
            return db.session.get(DatabaseProject, project.uid)
        return project

    def get_all_projects(
        self, root_schema_uid: Optional[UUID] = None
    ) -> Iterable[DatabaseProject]:
        query = select(DatabaseProject)
        if root_schema_uid is not None:
            query = query.filter_by(root_schema_uid=root_schema_uid)
        return db.session.scalars(query)

    def get_dataset(self, dataset: Union[UUID, Dataset, DatabaseDataset]):
        if isinstance(dataset, UUID):
            return db.session.get_one(DatabaseDataset, dataset)
        elif isinstance(dataset, Dataset):
            return db.session.get_one(DatabaseDataset, dataset.uid)
        return dataset

    def get_batch(self, batch: Union[UUID, Batch, DatabaseBatch]):
        if isinstance(batch, UUID):
            return db.session.get_one(DatabaseBatch, batch)
        elif isinstance(batch, Batch):
            return db.session.get_one(DatabaseBatch, batch.uid)
        return batch

    def get_optional_batch(self, batch: Union[UUID, Batch, DatabaseBatch]):
        if isinstance(batch, UUID):
            return db.session.get(DatabaseBatch, batch)
        elif isinstance(batch, Batch):
            return db.session.get(DatabaseBatch, batch.uid)
        return batch

    def get_attribute(self, attribute: Union[UUID, Attribute, DatabaseAttribute]):
        if isinstance(attribute, UUID):
            return DatabaseAttribute.get(attribute)
        elif isinstance(attribute, Attribute):
            return DatabaseAttribute.get(attribute.uid)
        return attribute

    def get_attributes_for_schema(self, attribute_schema: Union[UUID, AttributeSchema]):
        if isinstance(attribute_schema, AttributeSchema):
            attribute_schema = attribute_schema.uid
        return db.session.scalars(
            select(DatabaseAttribute).filter_by(schema_uid=attribute_schema)
        )

    def get_item(
        self, item: Union[UUID, ItemType, DatabaseItem[ItemType]]
    ) -> DatabaseItem[ItemType]:
        if isinstance(item, UUID):
            return DatabaseItem.get(item)
        elif isinstance(item, Item):
            return DatabaseItem.get(item.uid)
        return item

    def get_optional_item(
        self, item: Union[UUID, ItemType, DatabaseItem[ItemType]]
    ) -> Optional[DatabaseItem[ItemType]]:
        if isinstance(item, UUID):
            return DatabaseItem.get_optional(item)
        elif isinstance(item, Item):
            return DatabaseItem.get_optional(item.uid)
        return item

    def get_sample(self, sample: Union[UUID, Sample, DatabaseSample]):
        if isinstance(sample, UUID):
            return DatabaseSample.get(sample)
        elif isinstance(sample, Sample):
            return DatabaseSample.get(sample.uid)
        return sample

    def get_image(self, image: Union[UUID, Image, DatabaseImage]):
        if isinstance(image, UUID):
            return DatabaseImage.get(image)
        elif isinstance(image, Image):
            return DatabaseImage.get(image.uid)
        return image

    def get_observation(
        self, observation: Union[UUID, Observation, DatabaseObservation]
    ):
        if isinstance(observation, UUID):
            return DatabaseObservation.get(observation)
        elif isinstance(observation, Observation):
            return DatabaseObservation.get(observation.uid)
        return observation

    def get_annotation(self, annotation: Union[UUID, Annotation, DatabaseAnnotation]):
        if isinstance(annotation, UUID):
            return DatabaseAnnotation.get(annotation)
        elif isinstance(annotation, Annotation):
            return DatabaseAnnotation.get(annotation.uid)
        return annotation

    def get_sample_children(
        self,
        sample: Union[UUID, Sample, DatabaseSample],
        sample_schema: Union[UUID, SampleSchema],
        recursive: bool = False,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> Set["DatabaseSample"]:
        if isinstance(sample, UUID):
            sample = DatabaseSample.get(sample)
        elif isinstance(sample, Sample):
            sample = DatabaseSample.get(sample.uid)
        if sample.children is None:
            return set()
        if isinstance(sample_schema, SampleSchema):
            sample_schema = sample_schema.uid
        children = set(
            [
                child
                for child in sample.children
                if child.schema_uid == sample_schema
                and (selected is None or child.selected == selected)
                and (valid is None or child.valid == valid)
            ]
        )
        if recursive:
            for child in sample.children:
                children.update(
                    self.get_sample_children(
                        child, sample_schema, True, selected, valid
                    )
                )
        return children

    def get_sample_parents(
        self,
        sample: Union[UUID, Sample, DatabaseSample],
        sample_schema: Union[UUID, SampleSchema],
        recursive: bool = False,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> Set["DatabaseSample"]:
        if isinstance(sample, UUID):
            sample = DatabaseSample.get(sample)
        elif isinstance(sample, Sample):
            sample = DatabaseSample.get(sample.uid)
        if sample.parents is None:
            return set()
        if isinstance(sample_schema, SampleSchema):
            sample_schema = sample_schema.uid
        parents = set(
            [
                parent
                for parent in sample.parents
                if parent.schema_uid == sample_schema
                and (selected is None or parent.selected == selected)
                and (valid is None or parent.valid == valid)
            ]
        )
        if recursive:
            for parent in sample.parents:
                parents.update(
                    self.get_sample_parents(
                        parent, sample_schema, True, selected, valid
                    )
                )
        return parents

    def get_sample_images(
        self,
        sample: Union[UUID, Sample, DatabaseSample],
        image_schema: Union[UUID, ImageSchema],
        recursive: bool = False,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> Set[DatabaseImage]:
        if isinstance(sample, UUID):
            sample = DatabaseSample.get(sample)
        elif isinstance(sample, Sample):
            sample = DatabaseSample.get(sample.uid)
        if sample.images is None:
            return set()
        if isinstance(image_schema, ImageSchema):
            image_schema = image_schema.uid
        images = set(
            [
                image
                for image in sample.images
                if image.schema_uid == image_schema
                and (selected is None or image.selected == selected)
                and (valid is None or image.valid == valid)
            ]
        )
        if recursive:
            for parent in sample.parents:
                images.update(
                    self.get_sample_images(parent, image_schema, True, selected, valid)
                )
        return images

    def get_sample_child(
        self,
        sample: Union[UUID, Sample, DatabaseSample],
        identifier: str,
        schema: Union[UUID, SampleSchema],
    ) -> Optional["DatabaseSample"]:
        return next(
            (
                child
                for child in self.get_sample_children(sample, schema)
                if child.identifier == identifier
            ),
            None,
        )

    def get_image_in_sample(
        self,
        sample: Union[UUID, Sample, DatabaseSample],
        identifier: str,
    ) -> Optional[DatabaseImage]:
        if isinstance(sample, UUID):
            sample = DatabaseSample.get(sample)
        elif isinstance(sample, Sample):
            sample = DatabaseSample.get(sample.uid)
        return next(
            (image for image in sample.images if image.identifier == identifier), None
        )

    def get_image_samples(
        self,
        image: Union[UUID, Image, DatabaseImage],
        schema: Optional[Union[UUID, SampleSchema]] = None,
    ) -> Iterable[DatabaseSample]:
        if isinstance(image, UUID):
            image = DatabaseImage.get(image)
        elif isinstance(image, Image):
            image = DatabaseImage.get(image.uid)
        if isinstance(schema, SampleSchema):
            schema = schema.uid
        return (
            sample
            for sample in image.samples
            if sample.schema_uid == schema or schema is None
        )

    def get_items(
        self,
        dataset: Optional[Union[UUID, Dataset, DatabaseDataset]] = None,
        batch: Optional[Union[UUID, Batch, DatabaseBatch]] = None,
        schema: Optional[Union[UUID, ItemSchema]] = None,
        selected: Optional[bool] = None,
    ):
        if isinstance(dataset, (Dataset, DatabaseDataset)):
            dataset = dataset.uid
        if isinstance(batch, (Batch, DatabaseBatch)):
            batch = batch.uid
        if isinstance(schema, ItemSchema):
            schema = schema.uid
        query = select(DatabaseItem)
        if dataset is not None:
            query = query.filter_by(dataset_uid=dataset)
        if batch is not None:
            query = query.filter_by(batch_uid=batch)
        if schema is not None:
            query = query.filter_by(schema_uid=schema)
        if selected is not None:
            query = query.filter_by(selected=selected)
        return db.session.scalars(query)

    def get_images(
        self,
        dataset: Optional[Union[UUID, Dataset, DatabaseDataset]] = None,
        batch: Optional[Union[UUID, Batch, DatabaseBatch]] = None,
        schema: Optional[Union[UUID, ImageSchema]] = None,
        start: Optional[int] = None,
        size: Optional[int] = None,
        identifier_filter: Optional[str] = None,
        attributes_filters: Optional[Dict[str, str]] = None,
        sorting: Optional[Iterable[ColumnSort]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
        status_filter: Optional[Iterable[ImageStatus]] = None,
    ) -> Iterable[DatabaseImage]:
        query = self._query_items_for_batch_and_schema(
            select(DatabaseImage),
            dataset=dataset,
            batch=batch,
            schema=schema,
            identifier_filter=identifier_filter,
            attributes_filters=attributes_filters,
            selected=selected,
            valid=valid,
        )
        if status_filter is not None:
            query = query.filter(DatabaseImage.status.in_(status_filter))
        query = self._sort_and_limit_item_query(query, sorting, start, size)
        return db.session.scalars(query)

    def get_samples(
        self,
        dataset: Optional[Union[UUID, Dataset, DatabaseDataset]] = None,
        batch: Optional[Union[UUID, Batch, DatabaseBatch]] = None,
        schema: Optional[Union[UUID, SampleSchema]] = None,
        start: Optional[int] = None,
        size: Optional[int] = None,
        identifier_filter: Optional[str] = None,
        attributes_filters: Optional[Dict[str, str]] = None,
        sorting: Optional[Iterable[ColumnSort]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> Iterable[DatabaseSample]:
        query = self._query_items_for_batch_and_schema(
            select(DatabaseSample),
            dataset=dataset,
            batch=batch,
            schema=schema,
            identifier_filter=identifier_filter,
            attributes_filters=attributes_filters,
            selected=selected,
            valid=valid,
        )
        query = self._sort_and_limit_item_query(query, sorting, start, size)
        return db.session.scalars(query)

    def get_observations(
        self,
        dataset: Optional[Union[UUID, Dataset, DatabaseDataset]] = None,
        batch: Optional[Union[UUID, Batch, DatabaseBatch]] = None,
        schema: Optional[Union[UUID, ObservationSchema]] = None,
        start: Optional[int] = None,
        size: Optional[int] = None,
        identifier_filter: Optional[str] = None,
        attributes_filters: Optional[Dict[str, str]] = None,
        sorting: Optional[Iterable[ColumnSort]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> Iterable[DatabaseObservation]:
        query = self._query_items_for_batch_and_schema(
            select(DatabaseObservation),
            dataset=dataset,
            batch=batch,
            schema=schema,
            identifier_filter=identifier_filter,
            attributes_filters=attributes_filters,
            selected=selected,
            valid=valid,
        )
        query = self._sort_and_limit_item_query(query, sorting, start, size)
        return db.session.scalars(query)

    def get_annotations(
        self,
        dataset: Optional[Union[UUID, Dataset, DatabaseDataset]] = None,
        batch: Optional[Union[UUID, Batch, DatabaseBatch]] = None,
        schema: Optional[Union[UUID, AnnotationSchema]] = None,
        start: Optional[int] = None,
        size: Optional[int] = None,
        identifier_filter: Optional[str] = None,
        attributes_filters: Optional[Dict[str, str]] = None,
        sorting: Optional[Iterable[ColumnSort]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> Iterable[DatabaseAnnotation]:
        query = self._query_items_for_batch_and_schema(
            select(DatabaseAnnotation),
            dataset=dataset,
            batch=batch,
            schema=schema,
            identifier_filter=identifier_filter,
            attributes_filters=attributes_filters,
            selected=selected,
            valid=valid,
        )
        query = self._sort_and_limit_item_query(query, sorting, start, size)
        return db.session.scalars(query)

    def get_item_count(
        self,
        dataset: Optional[Union[UUID, Dataset, DatabaseDataset]] = None,
        batch: Optional[Union[UUID, Batch, DatabaseBatch]] = None,
        schema: Optional[Union[UUID, ItemSchema]] = None,
        identifier_filter: Optional[str] = None,
        attributes_filters: Optional[Dict[str, str]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
        status_filter: Optional[Iterable[ImageStatus]] = None,
    ) -> int:
        if isinstance(dataset, (Dataset, DatabaseDataset)):
            dataset = dataset.uid
        if isinstance(batch, (Batch, DatabaseBatch)):
            batch = batch.uid
        if isinstance(schema, ItemSchema):
            schema = schema.uid
        query = self._query_items_for_batch_and_schema(
            select(func.count(DatabaseItem.uid)),
            dataset=dataset,
            batch=batch,
            schema=schema,
            identifier_filter=identifier_filter,
            attributes_filters=attributes_filters,
            selected=selected,
            valid=valid,
        )
        if status_filter is not None:
            query = query.filter(DatabaseImage.status.in_(status_filter))

        return db.session.scalars(query).one()

    def delete_items(
        self,
        batch: Union[UUID, Batch, DatabaseBatch],
        schema: Union[UUID, ItemSchema],
        only_non_selected=False,
    ):
        if isinstance(batch, (Batch, DatabaseBatch)):
            batch = batch.uid
        if isinstance(schema, ItemSchema):
            schema = schema.uid
        query = select(DatabaseItem)
        query = self._limit_query(
            query,
            batch_uid=batch,
            schema_uid=schema,
            selected=False if only_non_selected else None,
        )
        for item in db.session.scalars(query):
            db.session.delete(item)
        db.session.commit()

    def add_item(self, item: ItemType, commit: bool = True) -> DatabaseItem[ItemType]:
        if isinstance(item, Sample):
            return DatabaseSample(
                item.dataset_uid,
                item.batch_uid,
                item.schema_uid,
                item.identifier,
                pseudonym=item.pseudonym,
                parents=[DatabaseSample.get(parent) for parent in item.parents],
                children=[DatabaseSample.get(child) for child in item.children],
                uid=item.uid,
                commit=commit,
            )  # type: ignore
        if isinstance(item, Image):
            return DatabaseImage(
                item.dataset_uid,
                item.batch_uid,
                item.schema_uid,
                item.identifier,
                pseudonym=item.pseudonym,
                samples=[DatabaseSample.get(sample) for sample in item.samples],
                files=[
                    DatabaseImageFile(file.filename, commit=commit)
                    for file in item.files
                ],
                folder_path=item.folder_path,
                thumbnail_path=item.thumbnail_path,
                uid=item.uid,
                commit=commit,
            )  # type: ignore
        if isinstance(item, Annotation):
            return DatabaseAnnotation(
                item.dataset_uid,
                item.batch_uid,
                item.schema_uid,
                item.identifier,
                pseudonym=item.pseudonym,
                image=DatabaseImage.get(item.image) if item.image else None,
                uid=item.uid,
                commit=commit,
            )  # type: ignore
        if isinstance(item, Observation):
            if item.sample is not None:
                observation_item = DatabaseSample.get(item.sample)
            elif item.image is not None:
                observation_item = DatabaseImage.get(item.image)
            elif item.annotation is not None:
                observation_item = DatabaseAnnotation.get(item.annotation)
            else:
                raise ValueError("Observation must have an item to observe.")
            return DatabaseObservation(
                item.dataset_uid,
                item.batch_uid,
                item.schema_uid,
                item.identifier,
                pseudonym=item.pseudonym,
                item=observation_item,
                uid=item.uid,
                commit=commit,
            )  # type: ignore
        raise TypeError(f"Unknown item type {item}.")

    def add_attribute(
        self,
        attribute: Attribute,
        attribute_schema: AttributeSchema,
        commit: bool = True,
    ) -> DatabaseAttribute:
        if isinstance(attribute, StringAttribute) and isinstance(
            attribute_schema, StringAttributeSchema
        ):
            return DatabaseStringAttribute(
                attribute_schema.tag,
                attribute_schema.uid,
                attribute.original_value,
                attribute.updated_value,
                attribute.mapped_value,
                mappable_value=attribute.mappable_value,
                commit=commit,
            )
        if isinstance(attribute, EnumAttribute) and isinstance(
            attribute_schema, EnumAttributeSchema
        ):
            return DatabaseEnumAttribute(
                attribute_schema.tag,
                attribute_schema.uid,
                attribute.original_value,
                attribute.updated_value,
                attribute.mapped_value,
                mappable_value=attribute.mappable_value,
                commit=commit,
            )
        if isinstance(attribute, DatetimeAttribute) and isinstance(
            attribute_schema, DatetimeAttributeSchema
        ):
            return DatabaseDatetimeAttribute(
                attribute_schema.tag,
                attribute_schema.uid,
                attribute.original_value,
                attribute.updated_value,
                attribute.mapped_value,
                mappable_value=attribute.mappable_value,
                commit=commit,
            )
        if isinstance(attribute, NumericAttribute) and isinstance(
            attribute_schema, NumericAttributeSchema
        ):
            return DatabaseNumericAttribute(
                attribute_schema.tag,
                attribute_schema.uid,
                attribute.original_value,
                attribute.updated_value,
                attribute.mapped_value,
                mappable_value=attribute.mappable_value,
                commit=commit,
            )
        if isinstance(attribute, MeasurementAttribute) and isinstance(
            attribute_schema, MeasurementAttributeSchema
        ):
            return DatabaseMeasurementAttribute(
                attribute_schema.tag,
                attribute_schema.uid,
                attribute.original_value,
                attribute.updated_value,
                attribute.mapped_value,
                mappable_value=attribute.mappable_value,
                commit=commit,
            )
        if isinstance(attribute, CodeAttribute) and isinstance(
            attribute_schema, CodeAttributeSchema
        ):
            return DatabaseCodeAttribute(
                attribute_schema.tag,
                attribute_schema.uid,
                attribute.original_value,
                attribute.updated_value,
                attribute.mapped_value,
                mappable_value=attribute.mappable_value,
                commit=commit,
            )
        if isinstance(attribute, BooleanAttribute) and isinstance(
            attribute_schema, BooleanAttributeSchema
        ):
            return DatabaseBooleanAttribute(
                attribute_schema.tag,
                attribute_schema.uid,
                attribute.original_value,
                attribute.updated_value,
                attribute.mapped_value,
                mappable_value=attribute.mappable_value,
                commit=commit,
            )
        if isinstance(attribute, ObjectAttribute) and isinstance(
            attribute_schema, ObjectAttributeSchema
        ):
            return DatabaseObjectAttribute(
                attribute_schema.tag,
                attribute_schema.uid,
                dict(attribute.original_value) if attribute.original_value else None,
                dict(attribute.updated_value) if attribute.updated_value else None,
                dict(attribute.mapped_value) if attribute.mapped_value else None,
                mappable_value=attribute.mappable_value,
                display_value_format_string=attribute_schema.display_value_format_string,
                commit=commit,
            )
        if isinstance(attribute, ListAttribute) and isinstance(
            attribute_schema, ListAttributeSchema
        ):
            return DatabaseListAttribute(
                attribute_schema.tag,
                attribute_schema.uid,
                attribute.original_value,
                attribute.updated_value,
                attribute.mapped_value,
                mappable_value=attribute.mappable_value,
                commit=commit,
            )
        if isinstance(attribute, UnionAttribute) and isinstance(
            attribute_schema, UnionAttributeSchema
        ):
            return DatabaseUnionAttribute(
                attribute_schema.tag,
                attribute_schema.uid,
                attribute.original_value,
                attribute.updated_value,
                attribute.mapped_value,
                mappable_value=attribute.mappable_value,
                commit=commit,
            )
        raise NotImplementedError(f"Non-implemented create for {attribute_schema}")

    @classmethod
    def _query_items_for_batch_and_schema(
        cls,
        query: Select,
        dataset: Optional[Union[UUID, Dataset, DatabaseDataset]] = None,
        batch: Optional[Union[UUID, Batch, DatabaseBatch]] = None,
        schema: Optional[Union[UUID, ItemSchema]] = None,
        identifier_filter: Optional[str] = None,
        attributes_filters: Optional[Dict[str, str]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> Select:
        if isinstance(dataset, (Dataset, DatabaseDataset)):
            dataset = dataset.uid
        if isinstance(batch, (Batch, DatabaseBatch)):
            batch = batch.uid
        if isinstance(schema, ItemSchema):
            schema = schema.uid
        return cls._limit_query(
            query,
            dataset,
            batch,
            schema,
            identifier_filter,
            attributes_filters,
            selected,
            valid,
        )

    @staticmethod
    def _limit_query(
        query: Select,
        dataset_uid: Optional[UUID] = None,
        batch_uid: Optional[UUID] = None,
        schema_uid: Optional[UUID] = None,
        identifier_filter: Optional[str] = None,
        attributes_filters: Optional[Dict[str, str]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ):
        if dataset_uid is not None:
            query = query.filter_by(dataset_uid=dataset_uid)
        if batch_uid is not None:
            query = query.filter_by(batch_uid=batch_uid)
        if schema_uid is not None:
            query = query.filter_by(schema_uid=schema_uid)
        if identifier_filter is not None:
            query = query.filter(DatabaseItem.identifier.icontains(identifier_filter))
        if attributes_filters is not None:
            for tag, value in attributes_filters.items():
                query = query.filter(
                    DatabaseItem.attributes.any(
                        and_(
                            DatabaseAttribute.display_value.icontains(value),
                            DatabaseAttribute.tag.is_(tag),
                        )
                    )
                )
        if selected is not None:
            query = query.filter_by(selected=selected)
        if valid is not None:
            query = query.filter_by(valid=valid)
        return query

    @staticmethod
    def _sort_and_limit_item_query(
        query: Select,
        sorting: Optional[Iterable[ColumnSort]] = None,
        start: Optional[int] = None,
        size: Optional[int] = None,
    ):
        if sorting is not None:
            for sort in sorting:
                if not sort.is_attribute:
                    if sort.column == "identifier":
                        sort_by = DatabaseItem.identifier
                    elif sort.column == "valid":
                        sort_by = DatabaseItem.valid
                    elif sort.column == "status":
                        sort_by = DatabaseImage.status
                    elif sort.column == "message":
                        sort_by = DatabaseImage.status_message
                    else:
                        raise NotImplementedError(f"Got unknown column {sort.column}.")
                    if sort.descending:
                        sort_by = sort_by.desc()
                    query = query.order_by(sort_by)
                else:
                    sort_by = DatabaseAttribute.display_value
                    if sort.descending:
                        sort_by = sort_by.desc()
                    query = (
                        query.join(DatabaseAttribute)
                        .where(DatabaseAttribute.tag.is_(sort.column))
                        .order_by(sort_by)
                    )

        if start is not None:
            query = query.offset(start)
        if size is not None:
            query = query.limit(size)
        return query
