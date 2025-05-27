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
import re
from contextlib import contextmanager
from typing import Dict, Iterable, Iterator, Optional, Set, TypeVar, Union
from uuid import UUID

from sqlalchemy import Select, and_, create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from slidetap.database import (
    Base,
    DatabaseAnnotation,
    DatabaseAttribute,
    DatabaseBatch,
    DatabaseBooleanAttribute,
    DatabaseCodeAttribute,
    DatabaseDataset,
    DatabaseDatetimeAttribute,
    DatabaseEnumAttribute,
    DatabaseImage,
    DatabaseImageFile,
    DatabaseItem,
    DatabaseListAttribute,
    DatabaseMapper,
    DatabaseMapperGroup,
    DatabaseMappingItem,
    DatabaseMeasurementAttribute,
    DatabaseNumericAttribute,
    DatabaseObjectAttribute,
    DatabaseObservation,
    DatabaseProject,
    DatabaseSample,
    DatabaseStringAttribute,
    DatabaseUnionAttribute,
)
from slidetap.model import (
    Annotation,
    AnnotationSchema,
    Attribute,
    AttributeSchema,
    AttributeType,
    Batch,
    BatchStatus,
    BooleanAttribute,
    BooleanAttributeSchema,
    CodeAttribute,
    CodeAttributeSchema,
    ColumnSort,
    Dataset,
    DatetimeAttribute,
    DatetimeAttributeSchema,
    EnumAttribute,
    EnumAttributeSchema,
    Image,
    ImageSchema,
    ImageStatus,
    Item,
    ItemSchema,
    ItemType,
    ListAttribute,
    ListAttributeSchema,
    Mapper,
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

DatabaseEnitity = TypeVar("DatabaseEnitity")


class DatabaseService:
    def __init__(self, database_uri: str):
        self._database_uri = database_uri
        self._engine = create_engine(self._database_uri)
        self._database_initialized = False

    def _init_database(self):
        Base.metadata.create_all(bind=self._engine)

    def create_session(self, autoflush: bool = True):
        if not self._database_initialized:
            self._init_database()
            self._database_initialized = True
        return sessionmaker(autoflush=autoflush, bind=self._engine)

    @contextmanager
    def get_session(
        self, session: Optional[Session] = None, commit: Optional[bool] = None
    ) -> Iterator[Session]:
        if session is None:
            session = self.create_session()()
            yield session
            if commit is None or commit:
                # Commit unless explicit no comit
                session.commit()
            session.close()
        else:
            yield session
            if commit:
                # Commit only if explicit
                session.commit()

    def get_project(
        self,
        session: Session,
        project: Union[UUID, Project, DatabaseProject],
    ):
        if isinstance(project, UUID):
            return session.get_one(DatabaseProject, project)
        elif isinstance(project, Project):
            return session.get_one(DatabaseProject, project.uid)
        return project

    def get_optional_project(
        self,
        session: Session,
        project: Union[UUID, Project, DatabaseProject],
    ) -> Optional[DatabaseProject]:
        if isinstance(project, UUID):
            return session.get(DatabaseProject, project)
        elif isinstance(project, Project):
            return session.get(DatabaseProject, project.uid)
        return project

    def get_all_projects(
        self,
        session: Session,
        root_schema_uid: Optional[UUID] = None,
    ) -> Iterable[DatabaseProject]:
        query = select(DatabaseProject)
        if root_schema_uid is not None:
            query = query.filter_by(root_schema_uid=root_schema_uid)
        return session.scalars(query)

    def get_dataset(
        self,
        session: Session,
        dataset: Union[UUID, Dataset, DatabaseDataset],
    ):
        database_dataset = self.get_optional_dataset(session, dataset)
        if database_dataset is None:
            raise ValueError(f"Dataset with uid {dataset} does not exist")
        return database_dataset

    def get_optional_dataset(
        self,
        session: Session,
        dataset: Union[UUID, Dataset, DatabaseDataset],
    ) -> Optional[DatabaseDataset]:
        if isinstance(dataset, UUID):
            return session.get(DatabaseDataset, dataset)
        elif isinstance(dataset, Dataset):
            return session.get(DatabaseDataset, dataset.uid)
        return dataset

    def get_batch(
        self,
        session: Session,
        batch: Union[UUID, Batch, DatabaseBatch],
    ):
        if isinstance(batch, UUID):
            return session.get_one(DatabaseBatch, batch)
        elif isinstance(batch, Batch):
            return session.get_one(DatabaseBatch, batch.uid)
        return batch

    def get_optional_batch(
        self,
        session: Session,
        batch: Union[UUID, Batch, DatabaseBatch],
    ):
        if isinstance(batch, UUID):
            return session.get(DatabaseBatch, batch)
        elif isinstance(batch, Batch):
            return session.get(DatabaseBatch, batch.uid)
        return batch

    def get_attribute(
        self,
        session: Session,
        attribute: Union[UUID, Attribute, DatabaseAttribute],
    ):

        if isinstance(attribute, UUID):
            return session.get_one(DatabaseAttribute, attribute)
        elif isinstance(attribute, Attribute):
            return session.get_one(DatabaseAttribute, attribute.uid)
        return attribute

    def get_attributes_for_schema(
        self,
        session: Session,
        attribute_schema: Union[UUID, AttributeSchema],
    ):
        if isinstance(attribute_schema, AttributeSchema):
            attribute_schema = attribute_schema.uid
        return session.scalars(
            select(DatabaseAttribute).filter_by(schema_uid=attribute_schema)
        )

    def get_item(
        self,
        session: Session,
        item: Union[UUID, ItemType, DatabaseItem[ItemType]],
    ) -> DatabaseItem[ItemType]:
        database_item = self.get_optional_item(session, item)
        if database_item is None:
            raise ValueError(f"Item with uid {item} does not exist")
        return database_item

    def get_optional_item(
        self,
        session: Session,
        item: Union[UUID, ItemType, DatabaseItem[ItemType]],
    ) -> Optional[DatabaseItem[ItemType]]:

        if isinstance(item, UUID):
            return session.get(DatabaseItem, item)
        elif isinstance(item, Item):
            return session.get(DatabaseItem, item.uid)
        return item

    def get_sample(
        self,
        session: Session,
        sample: Union[UUID, Sample, DatabaseSample],
    ) -> DatabaseSample:
        database_sample = self.get_optional_sample(session, sample)
        if database_sample is None:
            raise ValueError(f"Sample with uid {sample} does not exist")
        return database_sample

    def get_optional_sample(
        self,
        session: Session,
        sample: Union[UUID, Sample, DatabaseSample],
    ):

        if isinstance(sample, UUID):
            return session.get(DatabaseSample, sample)
        elif isinstance(sample, Sample):
            return session.get(DatabaseSample, sample.uid)
        return sample

    def get_image(
        self,
        session: Session,
        image: Union[UUID, Image, DatabaseImage],
    ) -> DatabaseImage:
        database_image = self.get_optional_image(session, image)
        if database_image is None:
            raise ValueError(f"Image with uid {image} does not exist")
        return database_image

    def get_optional_image(
        self,
        session: Session,
        image: Union[UUID, Image, DatabaseImage],
    ):

        if isinstance(image, UUID):
            return session.get(DatabaseImage, image)
        elif isinstance(image, Image):
            return session.get(DatabaseImage, image.uid)
        return image

    def get_observation(
        self,
        session: Session,
        observation: Union[UUID, Observation, DatabaseObservation],
    ) -> DatabaseObservation:
        database_observation = self.get_optional_observation(session, observation)
        if database_observation is None:
            raise ValueError(f"Observation with uid {observation} does not exist")
        return database_observation

    def get_optional_observation(
        self,
        session: Session,
        observation: Union[UUID, Observation, DatabaseObservation],
    ):

        if isinstance(observation, UUID):
            return session.get(DatabaseObservation, observation)
        elif isinstance(observation, Observation):
            return session.get(DatabaseObservation, observation.uid)
        return observation

    def get_annotation(
        self,
        session: Session,
        annotation: Union[UUID, Annotation, DatabaseAnnotation],
    ):
        database_annotation = self.get_optional_annotation(session, annotation)
        if database_annotation is None:
            raise ValueError(f"Annotation with uid {annotation} does not exist")
        return database_annotation

    def get_optional_annotation(
        self,
        session: Session,
        annotation: Union[UUID, Annotation, DatabaseAnnotation],
    ):

        if isinstance(annotation, UUID):
            return session.get(DatabaseAnnotation, annotation)
        elif isinstance(annotation, Annotation):
            return session.get(DatabaseAnnotation, annotation.uid)
        return annotation

    def get_sample_children(
        self,
        session: Session,
        sample: Union[UUID, Sample, DatabaseSample],
        sample_schema: Union[UUID, SampleSchema],
        recursive: bool = False,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
        batch_uid: Optional[UUID] = None,
    ) -> Set["DatabaseSample"]:
        sample = self.get_sample(session, sample)
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
                and (batch_uid is None or child.batch_uid == batch_uid)
            ]
        )
        if recursive:
            for child in sample.children:
                children.update(
                    self.get_sample_children(
                        session,
                        child,
                        sample_schema,
                        True,
                        selected,
                        valid,
                        batch_uid=batch_uid,
                    )
                )
        return children

    def get_sample_parents(
        self,
        session: Session,
        sample: Union[UUID, Sample, DatabaseSample],
        sample_schema: Union[UUID, SampleSchema],
        recursive: bool = False,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> Set["DatabaseSample"]:
        sample = self.get_sample(session, sample)
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
                        session,
                        parent,
                        sample_schema,
                        True,
                        selected,
                        valid,
                    )
                )
        return parents

    def get_sample_images(
        self,
        session: Session,
        sample: Union[UUID, Sample, DatabaseSample],
        image_schema: Union[UUID, ImageSchema],
        recursive: bool = False,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> Set[DatabaseImage]:
        sample = self.get_sample(session, sample)
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
                    self.get_sample_images(
                        session,
                        parent,
                        image_schema,
                        True,
                        selected,
                        valid,
                    )
                )
        return images

    def get_sample_child(
        self,
        session: Session,
        sample: Union[UUID, Sample, DatabaseSample],
        identifier: str,
        schema: Union[UUID, SampleSchema],
    ) -> Optional["DatabaseSample"]:
        return next(
            (
                child
                for child in self.get_sample_children(session, sample, schema)
                if child.identifier == identifier
            ),
            None,
        )

    def get_image_in_sample(
        self,
        session: Session,
        sample: Union[UUID, Sample, DatabaseSample],
        identifier: str,
    ) -> Optional[DatabaseImage]:
        sample = self.get_sample(session, sample)
        return next(
            (image for image in sample.images if image.identifier == identifier), None
        )

    def get_image_samples(
        self,
        session: Session,
        image: Union[UUID, Image, DatabaseImage],
        schema: Optional[Union[UUID, SampleSchema]] = None,
    ) -> Iterable[DatabaseSample]:
        image = self.get_image(session, image)
        if isinstance(schema, SampleSchema):
            schema = schema.uid
        return (
            sample
            for sample in image.samples
            if sample.schema_uid == schema or schema is None
        )

    def get_items(
        self,
        session: Session,
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

        return session.scalars(query)

    def get_images(
        self,
        session: Session,
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

        return session.scalars(query)

    def get_samples(
        self,
        session: Session,
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

        return session.scalars(query)

    def get_observations(
        self,
        session: Session,
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

        return session.scalars(query)

    def get_annotations(
        self,
        session: Session,
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

        return session.scalars(query)

    def get_item_count(
        self,
        session: Session,
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

        return session.scalars(query).one()

    def get_batches(
        self,
        session: Session,
        project: Optional[Union[UUID, Project, DatabaseProject]],
        status: Optional[BatchStatus],
    ) -> Iterable[DatabaseBatch]:
        query = select(DatabaseBatch)
        if project is not None:
            if isinstance(project, (Project, DatabaseProject)):
                project = project.uid
            query = query.where(DatabaseBatch.project_uid == project)
        if status is not None:
            query = query.where(DatabaseBatch.status == status)

        return session.scalars(query)

    def delete_items(
        self,
        session: Session,
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

        for item in session.scalars(query):
            session.delete(item)
        session.commit()

    def add_item(
        self,
        session: Session,
        item: ItemType,
        schema: ItemSchema,
    ) -> DatabaseItem[ItemType]:
        if isinstance(item, Sample):
            return self._add_to_session(
                session,
                DatabaseSample(
                    item.dataset_uid,
                    item.batch_uid,
                    item.schema_uid,
                    item.identifier,
                    name=item.name,
                    external_identifier=item.external_identifier,
                    pseudonym=item.pseudonym,
                    parents=[
                        parent
                        for parent in [
                            self.get_optional_sample(session, parent)
                            for parent in item.parents
                        ]
                        if parent is not None
                    ],
                    children=[
                        child
                        for child in [
                            self.get_optional_sample(session, child)
                            for child in item.children
                        ]
                        if child is not None
                    ],
                    attributes={
                        tag: self.add_attribute(
                            session, attribute, schema.attributes[tag]
                        )
                        for tag, attribute in item.attributes.items()
                    },
                    uid=item.uid,
                ),
            )  # type: ignore
        if isinstance(item, Image):
            image = DatabaseImage(
                item.dataset_uid,
                item.batch_uid,
                item.schema_uid,
                item.identifier,
                name=item.name,
                external_identifier=item.external_identifier,
                pseudonym=item.pseudonym,
                samples=[
                    sample
                    for sample in [
                        self.get_optional_sample(session, sample)
                        for sample in item.samples
                    ]
                    if sample is not None
                ],
                attributes={
                    tag: self.add_attribute(session, attribute, schema.attributes[tag])
                    for tag, attribute in item.attributes.items()
                },
                folder_path=item.folder_path,
                thumbnail_path=item.thumbnail_path,
                uid=item.uid,
            )
            image.files = [
                DatabaseImageFile(image, file.filename) for file in item.files
            ]
            return self._add_to_session(session, image)  # type: ignore

        if isinstance(item, Annotation):
            image = self.get_optional_image(session, item.image) if item.image else None
            return self._add_to_session(
                session,
                DatabaseAnnotation(
                    item.dataset_uid,
                    item.batch_uid,
                    item.schema_uid,
                    item.identifier,
                    name=item.name,
                    external_identifier=item.external_identifier,
                    pseudonym=item.pseudonym,
                    image=image,
                    attributes={
                        tag: self.add_attribute(
                            session, attribute, schema.attributes[tag]
                        )
                        for tag, attribute in item.attributes.items()
                    },
                    uid=item.uid,
                ),
            )  # type: ignore
        if isinstance(item, Observation):
            if item.sample is not None:
                observation_item = self.get_optional_sample(session, item.sample)
            elif item.image is not None:
                observation_item = self.get_optional_image(session, item.image)
            elif item.annotation is not None:
                observation_item = self.get_optional_annotation(
                    session, item.annotation
                )
            else:
                observation_item = None
            return self._add_to_session(
                session,
                DatabaseObservation(
                    item.dataset_uid,
                    item.batch_uid,
                    item.schema_uid,
                    item.identifier,
                    name=item.name,
                    external_identifier=item.external_identifier,
                    pseudonym=item.pseudonym,
                    item=observation_item,
                    uid=item.uid,
                ),
            )  # type: ignore
        raise TypeError(f"Unknown item type {item}.")

    def get_optional_attribute(
        self, session: Session, attribute: Union[UUID, Attribute, DatabaseAttribute]
    ) -> Optional[DatabaseAttribute]:
        if isinstance(attribute, UUID):
            return session.get(DatabaseAttribute, attribute)
        elif isinstance(attribute, Attribute):
            return session.get(DatabaseAttribute, attribute.uid)
        return attribute

    def add_attribute(
        self,
        session: Session,
        attribute: Attribute,
        attribute_schema: AttributeSchema,
    ) -> DatabaseAttribute:
        if isinstance(attribute, StringAttribute) and isinstance(
            attribute_schema, StringAttributeSchema
        ):
            return self._add_to_session(
                session,
                DatabaseStringAttribute(
                    attribute_schema.tag,
                    attribute_schema.uid,
                    attribute.original_value,
                    attribute.updated_value,
                    attribute.mapped_value,
                    mappable_value=attribute.mappable_value,
                    uid=attribute.uid,
                ),
            )
        if isinstance(attribute, EnumAttribute) and isinstance(
            attribute_schema, EnumAttributeSchema
        ):
            return self._add_to_session(
                session,
                DatabaseEnumAttribute(
                    attribute_schema.tag,
                    attribute_schema.uid,
                    attribute.original_value,
                    attribute.updated_value,
                    attribute.mapped_value,
                    mappable_value=attribute.mappable_value,
                    uid=attribute.uid,
                ),
            )
        if isinstance(attribute, DatetimeAttribute) and isinstance(
            attribute_schema, DatetimeAttributeSchema
        ):
            return self._add_to_session(
                session,
                DatabaseDatetimeAttribute(
                    attribute_schema.tag,
                    attribute_schema.uid,
                    attribute.original_value,
                    attribute.updated_value,
                    attribute.mapped_value,
                    mappable_value=attribute.mappable_value,
                    uid=attribute.uid,
                ),
            )
        if isinstance(attribute, NumericAttribute) and isinstance(
            attribute_schema, NumericAttributeSchema
        ):
            return self._add_to_session(
                session,
                DatabaseNumericAttribute(
                    attribute_schema.tag,
                    attribute_schema.uid,
                    attribute.original_value,
                    attribute.updated_value,
                    attribute.mapped_value,
                    mappable_value=attribute.mappable_value,
                    uid=attribute.uid,
                ),
            )
        if isinstance(attribute, MeasurementAttribute) and isinstance(
            attribute_schema, MeasurementAttributeSchema
        ):
            return self._add_to_session(
                session,
                DatabaseMeasurementAttribute(
                    attribute_schema.tag,
                    attribute_schema.uid,
                    attribute.original_value,
                    attribute.updated_value,
                    attribute.mapped_value,
                    mappable_value=attribute.mappable_value,
                    uid=attribute.uid,
                ),
            )

        if isinstance(attribute, CodeAttribute) and isinstance(
            attribute_schema, CodeAttributeSchema
        ):
            return self._add_to_session(
                session,
                DatabaseCodeAttribute(
                    attribute_schema.tag,
                    attribute_schema.uid,
                    attribute.original_value,
                    attribute.updated_value,
                    attribute.mapped_value,
                    mappable_value=attribute.mappable_value,
                    uid=attribute.uid,
                ),
            )
        if isinstance(attribute, BooleanAttribute) and isinstance(
            attribute_schema, BooleanAttributeSchema
        ):
            return self._add_to_session(
                session,
                DatabaseBooleanAttribute(
                    attribute_schema.tag,
                    attribute_schema.uid,
                    attribute.original_value,
                    attribute.updated_value,
                    attribute.mapped_value,
                    mappable_value=attribute.mappable_value,
                    uid=attribute.uid,
                ),
            )
        if isinstance(attribute, ObjectAttribute) and isinstance(
            attribute_schema, ObjectAttributeSchema
        ):
            return self._add_to_session(
                session,
                DatabaseObjectAttribute(
                    attribute_schema.tag,
                    attribute_schema.uid,
                    (
                        dict(attribute.original_value)
                        if attribute.original_value
                        else None
                    ),
                    dict(attribute.updated_value) if attribute.updated_value else None,
                    dict(attribute.mapped_value) if attribute.mapped_value else None,
                    mappable_value=attribute.mappable_value,
                    display_value_format_string=attribute_schema.display_value_format_string,
                    uid=attribute.uid,
                ),
            )
        if isinstance(attribute, ListAttribute) and isinstance(
            attribute_schema, ListAttributeSchema
        ):
            return self._add_to_session(
                session,
                DatabaseListAttribute(
                    attribute_schema.tag,
                    attribute_schema.uid,
                    attribute.original_value,
                    attribute.updated_value,
                    attribute.mapped_value,
                    mappable_value=attribute.mappable_value,
                    uid=attribute.uid,
                ),
            )
        if isinstance(attribute, UnionAttribute) and isinstance(
            attribute_schema, UnionAttributeSchema
        ):
            return self._add_to_session(
                session,
                DatabaseUnionAttribute(
                    attribute_schema.tag,
                    attribute_schema.uid,
                    attribute.original_value,
                    attribute.updated_value,
                    attribute.mapped_value,
                    mappable_value=attribute.mappable_value,
                    uid=attribute.uid,
                ),
            )
        raise NotImplementedError(
            f"Non-implemented create for {attribute} {attribute_schema}"
        )

    def add_batch(self, session: Session, batch: Batch) -> DatabaseBatch:
        return self._add_to_session(
            session,
            DatabaseBatch(
                name=batch.name,
                project_uid=batch.project_uid,
                created=batch.created,
                uid=batch.uid,
            ),
        )

    def add_dataset(self, session: Session, dataset: Dataset) -> DatabaseDataset:
        return self._add_to_session(
            session,
            DatabaseDataset(
                name=dataset.name,
                schema_uid=dataset.schema_uid,
                uid=dataset.uid,
            ),
        )

    def add_project(self, session: Session, project: Project) -> DatabaseProject:
        mapper_groups = [
            self.get_mapper_group(session, group) for group in project.mapper_groups
        ]
        return self._add_to_session(
            session,
            DatabaseProject(
                name=project.name,
                root_schema_uid=project.root_schema_uid,
                schema_uid=project.schema_uid,
                dataset_uid=project.dataset_uid,
                created=project.created,
                uid=project.uid,
                mapper_groups=mapper_groups,
            ),
        )

    def get_optional_item_by_identifier(
        self,
        session: Session,
        identifier: str,
        schema: Union[UUID, ItemSchema],
        dataset: Union[UUID, Dataset, DatabaseDataset],
        batch: Optional[Union[UUID, Batch, DatabaseBatch]] = None,
    ) -> Optional[DatabaseItem]:
        if isinstance(schema, ItemSchema):
            schema = schema.uid
        if isinstance(dataset, (Dataset, DatabaseDataset)):
            dataset = dataset.uid

        query = select(DatabaseItem).filter_by(
            identifier=identifier, schema_uid=schema, dataset_uid=dataset
        )
        if batch is not None:
            if isinstance(batch, (Batch, DatabaseBatch)):
                batch = batch.uid
            query = query.filter_by(batch_uid=batch)

        return session.scalars(query).one_or_none()

    def get_first_image_for_batch(
        self,
        session: Session,
        batch_uid: UUID,
        include_status: Iterable[ImageStatus] = [],
        exclude_status: Iterable[ImageStatus] = [],
        selected: Optional[bool] = None,
    ) -> Optional[DatabaseImage]:
        query = select(DatabaseImage).filter(DatabaseImage.batch_uid == batch_uid)
        for item in include_status:
            query = query.filter(DatabaseImage.status == item)
        for item in exclude_status:
            query = query.filter(DatabaseImage.status != item)
        if selected is not None:
            query = query.filter(DatabaseImage.selected == selected)
        return session.scalars(query).first()

    def get_mapping(self, session: Session, mapping_uid: UUID):
        return session.get_one(DatabaseMappingItem, mapping_uid)

    def get_mapping_for_expression(
        self, session: Session, mapper_uid: UUID, expression: str
    ):
        mapping = self.get_optional_mapping_for_expression(
            session, mapper_uid, expression
        )
        if mapping is None:
            raise ValueError(f"Mapping for expression {expression} does not exist")
        return mapping

    def get_optional_mapping_for_expression(
        self,
        session: Session,
        mapper_uid: UUID,
        expression: str,
    ):
        return session.scalars(
            select(DatabaseMappingItem).filter_by(
                mapper_uid=mapper_uid, expression=expression
            )
        ).one_or_none()

    def get_mappings_for_mapper(self, session: Session, mapper_uid: UUID):
        return session.scalars(
            select(DatabaseMappingItem).filter_by(mapper_uid=mapper_uid)
        )

    def get_mapper_expressions(self, session: Session, mapper_uid: UUID):
        return session.scalars(
            select(DatabaseMappingItem.expression)
            .where(
                DatabaseMappingItem.mapper_uid == mapper_uid,
            )
            .order_by(DatabaseMappingItem.hits.desc())
        )

    def add_mapping(
        self,
        session: Session,
        mapper_uid: UUID,
        expression: str,
        attribute: Attribute[AttributeType],
    ):
        return self._add_to_session(
            session,
            DatabaseMappingItem(mapper_uid, expression, attribute),
        )

    def get_mapping_for_value(
        self,
        session: Session,
        mapper: DatabaseMapper[AttributeType],
        mappable_value: str,
    ) -> Optional[DatabaseMappingItem[AttributeType]]:
        for expression in self.get_mapper_expressions(session, mapper.uid):
            if re.match(expression, mappable_value) is not None:
                return self.get_mapping_for_expression(session, mapper.uid, expression)
        return None

    def get_mapper(
        self,
        session: Session,
        mapper: Union[UUID, Mapper, DatabaseMapper],
    ) -> DatabaseMapper:
        if isinstance(mapper, UUID):
            return session.get_one(DatabaseMapper, mapper)
        if isinstance(mapper, Mapper):
            return session.get_one(DatabaseMapper, mapper.uid)
        return mapper

    def get_mapper_by_name(
        self,
        session: Session,
        name: str,
    ) -> Optional[DatabaseMapper]:
        return session.scalars(
            select(DatabaseMapper).filter_by(name=name)
        ).one_or_none()

    def get_mappers_for_root_attribute(
        self,
        session: Session,
        root_attribute_schema_uid: UUID,
        include_mapper_uids: Iterable[UUID],
    ):
        return session.scalars(
            select(DatabaseMapper)
            .filter_by(
                root_attribute_schema_uid=root_attribute_schema_uid,
            )
            .filter(
                DatabaseMapper.uid.in_(include_mapper_uids),
            )
        )

    def add_mapper(
        self,
        session: Session,
        name: str,
        attribute_schema_uid: UUID,
        root_attribute_schema_uid: UUID,
    ):
        return self._add_to_session(
            session,
            DatabaseMapper(
                name=name,
                attribute_schema_uid=attribute_schema_uid,
                root_attribute_schema_uid=root_attribute_schema_uid,
            ),
        )

    def get_mapper_groups(self, session: Session) -> Iterable[DatabaseMapperGroup]:
        return session.scalars(select(DatabaseMapperGroup))

    def get_mapper_group_by_name(
        self,
        session: Session,
        name: str,
    ):
        return session.scalars(
            select(DatabaseMapperGroup).filter_by(name=name)
        ).one_or_none()

    def get_mapper_group(
        self,
        session: Session,
        mapper_group: Union[UUID, DatabaseMapperGroup],
    ) -> DatabaseMapperGroup:
        if isinstance(mapper_group, UUID):
            return session.get_one(DatabaseMapperGroup, mapper_group)
        return mapper_group

    def add_mapper_group(
        self, session: Session, name: str, default_enabled: bool
    ) -> DatabaseMapperGroup:
        return self._add_to_session(
            session,
            DatabaseMapperGroup(name=name, default_enabled=default_enabled),
        )

    def get_default_mapper_groups(
        self, session: Session
    ) -> Iterable[DatabaseMapperGroup]:
        return session.scalars(
            select(DatabaseMapperGroup).filter_by(default_enabled=True)
        )

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

    def _add_to_session(
        self, session: Session, item: DatabaseEnitity
    ) -> DatabaseEnitity:
        session.add(item)
        return item
