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
from typing import (
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)
from uuid import UUID

from sqlalchemy import (
    Column,
    Label,
    Select,
    Table,
    and_,
    create_engine,
    func,
    select,
)
from sqlalchemy.orm import InstrumentedAttribute, Session, aliased, sessionmaker

from slidetap.config import DatabaseConfig
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
from slidetap.database.item import DatabaseTag
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
from slidetap.model.table import (
    AttributeSort,
    RelationFilter,
    RelationFilterType,
    RelationSort,
    SortType,
)
from slidetap.model.tag import Tag

DatabaseEnitity = TypeVar("DatabaseEnitity")


class DatabaseService:
    def __init__(self, config: DatabaseConfig):
        self._engine = create_engine(config.uri)
        self._no_autoflush = config.no_autoflush
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
        new_session = session is None
        if new_session:
            session = self.create_session()()
        if self._no_autoflush:
            session.autoflush = False
        yield session
        if (new_session and commit is None) or commit:
            # Commit by default if new session or if commit is explicitly set
            session.commit()
        if new_session:
            # Close session if it was created in this context
            session.close()

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
        sample_schema: Optional[Union[UUID, SampleSchema]] = None,
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
                if (sample_schema is None or child.schema_uid == sample_schema)
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
        image_schema: Optional[Union[UUID, ImageSchema]] = None,
        recursive: bool = False,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> Set[DatabaseImage]:
        sample = self.get_sample(session, sample)
        if len(sample.images) == 0 and not recursive:
            return set()
        if isinstance(image_schema, ImageSchema):
            image_schema = image_schema.uid
        images = set(
            [
                image
                for image in sample.images
                if (image_schema is None or image.schema_uid == image_schema)
                and (selected is None or image.selected == selected)
                and (valid is None or image.valid == valid)
            ]
        )
        if recursive:
            for child in sample.children:
                images.update(
                    self.get_sample_images(
                        session,
                        child,
                        image_schema,
                        True,
                        selected,
                        valid,
                    )
                )
        return images

    def get_observation_samples(
        self,
        session: Session,
        observation: Union[UUID, Observation, DatabaseObservation],
        sample_schema: Optional[Union[UUID, SampleSchema]] = None,
        recursive: bool = False,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> Set[DatabaseSample]:
        observation = self.get_observation(session, observation)
        if (
            observation.item is None
            or isinstance(observation.item, DatabaseImage)
            or isinstance(observation.item, DatabaseAnnotation)
        ):
            return set()
        if isinstance(sample_schema, SampleSchema):
            sample_schema = sample_schema.uid
        if isinstance(observation.item, DatabaseSample):
            if observation.item.schema_uid == sample_schema:
                return {observation.item}
            return self.get_sample_children(
                session, observation.item, sample_schema, recursive, selected, valid
            )
            return self.get_sample_children()

        raise ValueError()

    def get_observation_images(
        self,
        session: Session,
        observation: Union[UUID, Observation, DatabaseObservation],
        image_schema: Optional[Union[UUID, ImageSchema]] = None,
        recursive: bool = False,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> Set[DatabaseImage]:
        observation = self.get_observation(session, observation)
        if observation.item is None:
            return set()
        if isinstance(image_schema, ImageSchema):
            image_schema = image_schema.uid
        if isinstance(observation.item, DatabaseSample):
            return self.get_sample_images(
                session,
                observation.item,
                image_schema,
                recursive,
                selected,
                valid,
            )
        if isinstance(observation.item, DatabaseImage):
            if (
                (
                    image_schema is not None
                    and observation.item.schema_uid != image_schema
                )
                or (valid is not None and observation.item.valid != valid)
                or (selected is not None and observation.item.selected != selected)
            ):
                return set()
            return {observation.item}
        if isinstance(observation.item, DatabaseAnnotation):
            if observation.item.image is None:
                return set()
            if (
                observation.item.image.schema_uid != image_schema
                or (valid is not None and observation.item.image.valid != valid)
                or (
                    selected is not None and observation.item.image.selected != selected
                )
            ):
                return set()
            return {observation.item.image}
        raise ValueError()

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
        schema: ItemSchema,
        dataset: Optional[Union[UUID, Dataset, DatabaseDataset]] = None,
        batch: Optional[Union[UUID, Batch, DatabaseBatch]] = None,
        selected: Optional[bool] = None,
    ):
        if isinstance(dataset, (Dataset, DatabaseDataset)):
            dataset = dataset.uid
        if isinstance(batch, (Batch, DatabaseBatch)):
            batch = batch.uid
        if isinstance(schema, SampleSchema):
            query_item = DatabaseSample
        elif isinstance(schema, ImageSchema):
            query_item = DatabaseImage
        elif isinstance(schema, ObservationSchema):
            query_item = DatabaseObservation
        elif isinstance(schema, AnnotationSchema):
            query_item = DatabaseAnnotation
        else:
            raise TypeError(f"Unknown schema type {schema}.")
        query = select(query_item)
        if dataset is not None:
            query = query.filter_by(dataset_uid=dataset)
        if batch is not None:
            query = query.filter_by(batch_uid=batch)
        if schema is not None:
            query = query.filter_by(schema_uid=schema.uid)
        if selected is not None:
            query = query.filter_by(selected=selected)

        return session.scalars(query)

    def get_images(
        self,
        session: Session,
        schema: ImageSchema,
        dataset: Optional[Union[UUID, Dataset, DatabaseDataset]] = None,
        batch: Optional[Union[UUID, Batch, DatabaseBatch]] = None,
        start: Optional[int] = None,
        size: Optional[int] = None,
        identifier_filter: Optional[str] = None,
        attributes_filters: Optional[Dict[str, str]] = None,
        tag_filter: Optional[Iterable[UUID]] = None,
        relation_filters: Optional[Iterable[RelationFilter]] = None,
        sorting: Optional[Iterable[ColumnSort]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
        status_filter: Optional[Iterable[ImageStatus]] = None,
    ) -> Iterable[DatabaseImage]:
        return self._query_sort_and_limit_items(
            session,
            select_type=DatabaseImage,
            schema=schema,
            dataset=dataset,
            batch=batch,
            identifier_filter=identifier_filter,
            attributes_filters=attributes_filters,
            tag_filter=tag_filter,
            relation_filters=relation_filters,
            status_filter=status_filter,
            sorting=sorting,
            start=start,
            size=size,
            selected=selected,
            valid=valid,
        )

    def get_samples(
        self,
        session: Session,
        schema: SampleSchema,
        dataset: Optional[Union[UUID, Dataset, DatabaseDataset]] = None,
        batch: Optional[Union[UUID, Batch, DatabaseBatch]] = None,
        start: Optional[int] = None,
        size: Optional[int] = None,
        identifier_filter: Optional[str] = None,
        attributes_filters: Optional[Dict[str, str]] = None,
        tag_filter: Optional[Iterable[UUID]] = None,
        relation_filters: Optional[Iterable[RelationFilter]] = None,
        sorting: Optional[Iterable[ColumnSort]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> Iterable[DatabaseSample]:
        return self._query_sort_and_limit_items(
            session,
            select_type=DatabaseSample,
            schema=schema,
            dataset=dataset,
            batch=batch,
            identifier_filter=identifier_filter,
            attributes_filters=attributes_filters,
            tag_filter=tag_filter,
            relation_filters=relation_filters,
            sorting=sorting,
            start=start,
            size=size,
            selected=selected,
            valid=valid,
        )

    def get_observations(
        self,
        session: Session,
        schema: ObservationSchema,
        dataset: Optional[Union[UUID, Dataset, DatabaseDataset]] = None,
        batch: Optional[Union[UUID, Batch, DatabaseBatch]] = None,
        start: Optional[int] = None,
        size: Optional[int] = None,
        identifier_filter: Optional[str] = None,
        attributes_filters: Optional[Dict[str, str]] = None,
        tag_filter: Optional[Iterable[UUID]] = None,
        relation_filters: Optional[Iterable[RelationFilter]] = None,
        sorting: Optional[Iterable[ColumnSort]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> Iterable[DatabaseObservation]:
        return self._query_sort_and_limit_items(
            session,
            select_type=DatabaseObservation,
            schema=schema,
            dataset=dataset,
            batch=batch,
            identifier_filter=identifier_filter,
            attributes_filters=attributes_filters,
            tag_filter=tag_filter,
            relation_filters=relation_filters,
            sorting=sorting,
            start=start,
            size=size,
            selected=selected,
            valid=valid,
        )

    def get_annotations(
        self,
        session: Session,
        schema: AnnotationSchema,
        dataset: Optional[Union[UUID, Dataset, DatabaseDataset]] = None,
        batch: Optional[Union[UUID, Batch, DatabaseBatch]] = None,
        start: Optional[int] = None,
        size: Optional[int] = None,
        identifier_filter: Optional[str] = None,
        attributes_filters: Optional[Dict[str, str]] = None,
        tag_filter: Optional[Iterable[UUID]] = None,
        relation_filters: Optional[Iterable[RelationFilter]] = None,
        sorting: Optional[Iterable[ColumnSort]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> Iterable[DatabaseAnnotation]:
        return self._query_sort_and_limit_items(
            session,
            select_type=DatabaseAnnotation,
            schema=schema,
            dataset=dataset,
            batch=batch,
            identifier_filter=identifier_filter,
            attributes_filters=attributes_filters,
            tag_filter=tag_filter,
            relation_filters=relation_filters,
            sorting=sorting,
            start=start,
            size=size,
            selected=selected,
            valid=valid,
        )

    def get_item_count(
        self,
        session: Session,
        schema: ItemSchema,
        dataset: Optional[Union[UUID, Dataset, DatabaseDataset]] = None,
        batch: Optional[Union[UUID, Batch, DatabaseBatch]] = None,
        identifier_filter: Optional[str] = None,
        attributes_filters: Optional[Dict[str, str]] = None,
        tag_filter: Optional[Iterable[UUID]] = None,
        relation_filters: Optional[Iterable[RelationFilter]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
        status_filter: Optional[Iterable[ImageStatus]] = None,
    ) -> int:
        if isinstance(dataset, (Dataset, DatabaseDataset)):
            dataset = dataset.uid
        if isinstance(batch, (Batch, DatabaseBatch)):
            batch = batch.uid
        if isinstance(schema, SampleSchema):
            query_item = DatabaseSample
        elif isinstance(schema, ImageSchema):
            query_item = DatabaseImage
        elif isinstance(schema, ObservationSchema):
            query_item = DatabaseObservation
        elif isinstance(schema, AnnotationSchema):
            query_item = DatabaseAnnotation
        else:
            raise TypeError(f"Unknown schema type {schema}.")
        query = self._items_query(
            select(func.count(query_item.uid)),
            schema=schema,
            dataset_uid=dataset,
            batch_uid=batch,
            identifier_filter=identifier_filter,
            attributes_filters=attributes_filters,
            tag_filter=tag_filter,
            relation_filters=relation_filters,
            status_filter=status_filter,
            selected=selected,
            valid=valid,
        )
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
        schema: ItemSchema,
        batch: Union[UUID, Batch, DatabaseBatch],
        only_non_selected=False,
    ):
        if isinstance(batch, (Batch, DatabaseBatch)):
            batch = batch.uid
        query = select(DatabaseItem)
        query = self._items_query(
            select(DatabaseItem),
            schema=schema,
            batch_uid=batch,
            selected=False if only_non_selected else None,
        )

        for item in session.scalars(query):
            session.delete(item)
        session.commit()

    def add_item(
        self,
        session: Session,
        item: ItemType,
        attributes: List[DatabaseAttribute],
        private_attributes: List[DatabaseAttribute],
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
                            for schema in item.parents.values()
                            for parent in schema
                        ]
                        if parent is not None
                    ],
                    children=[
                        child
                        for child in [
                            self.get_optional_sample(session, child)
                            for schema in item.children.values()
                            for child in schema
                        ]
                        if child is not None
                    ],
                    attributes=attributes,
                    private_attributes=private_attributes,
                    comment=item.comment,
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
                        for schema in item.samples.values()
                        for sample in schema
                    ]
                    if sample is not None
                ],
                attributes=attributes,
                private_attributes=private_attributes,
                folder_path=item.folder_path,
                thumbnail_path=item.thumbnail_path,
                comment=item.comment,
                uid=item.uid,
            )
            image.files = set(
                DatabaseImageFile(image, file.filename) for file in item.files
            )
            return self._add_to_session(session, image)  # type: ignore

        if isinstance(item, Annotation):
            image = (
                self.get_optional_image(session, item.image[1]) if item.image else None
            )
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
                    attributes=attributes,
                    private_attributes=private_attributes,
                    comment=item.comment,
                    uid=item.uid,
                ),
            )  # type: ignore
        if isinstance(item, Observation):
            if item.sample is not None:
                observation_item = self.get_optional_sample(session, item.sample[1])
            elif item.image is not None:
                observation_item = self.get_optional_image(session, item.image[1])
            elif item.annotation is not None:
                observation_item = self.get_optional_annotation(
                    session, item.annotation[1]
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
                    attributes=attributes,
                    private_attributes=private_attributes,
                    comment=item.comment,
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
                    display_value=attribute.display_value,
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
                    display_value=attribute.display_value,
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
                    display_value=attribute.display_value,
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
                    display_value=attribute.display_value,
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
                    display_value=attribute.display_value,
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
                    display_value=attribute.display_value,
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
                    display_value=attribute.display_value,
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
                    display_value=attribute.display_value,
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
                    display_value=attribute.display_value,
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
                    display_value=attribute.display_value,
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

    def get_tags(self, session: Session) -> Iterable[DatabaseTag]:
        """Get all tags from the database."""
        return session.scalars(select(DatabaseTag))

    def get_optional_tag(
        self, session: Session, tag: Union[UUID, Tag, DatabaseTag]
    ) -> Optional[DatabaseTag]:
        if isinstance(tag, UUID):
            return session.get(DatabaseTag, tag)
        if isinstance(tag, Tag):
            return session.get(DatabaseTag, tag.uid)
        return tag

    def get_tag(
        self, session: Session, tag: Union[UUID, Tag, DatabaseTag]
    ) -> DatabaseTag:
        if isinstance(tag, UUID):
            tag = session.get_one(DatabaseTag, tag)
        elif isinstance(tag, Tag):
            tag = session.get_one(DatabaseTag, tag.uid)
        return tag

    def add_tag(self, session: Session, tag: Tag) -> DatabaseTag:
        """Add a new tag to the database."""
        return self._add_to_session(
            session,
            DatabaseTag(
                name=tag.name,
                color=tag.color,
                description=tag.description,
                uid=tag.uid,
            ),
        )

    @classmethod
    def _query_sort_and_limit_items(
        cls,
        session: Session,
        select_type: Type[DatabaseItem],
        schema: ItemSchema,
        dataset: Optional[Union[UUID, Dataset, DatabaseDataset]] = None,
        batch: Optional[Union[UUID, Batch, DatabaseBatch]] = None,
        start: Optional[int] = None,
        size: Optional[int] = None,
        identifier_filter: Optional[str] = None,
        attributes_filters: Optional[Dict[str, str]] = None,
        tag_filter: Optional[Iterable[UUID]] = None,
        relation_filters: Optional[Iterable[RelationFilter]] = None,
        status_filter: Optional[Iterable[ImageStatus]] = None,
        sorting: Optional[Iterable[ColumnSort]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ):
        if isinstance(dataset, (Dataset, DatabaseDataset)):
            dataset = dataset.uid
        if isinstance(batch, (Batch, DatabaseBatch)):
            batch = batch.uid
        query = cls._items_query(
            select(select_type),
            dataset_uid=dataset,
            batch_uid=batch,
            schema=schema,
            identifier_filter=identifier_filter,
            attributes_filters=attributes_filters,
            tag_filter=tag_filter,
            relation_filters=relation_filters,
            status_filter=status_filter,
            selected=selected,
            valid=valid,
        )
        query = cls._sort_and_limit_item_query(
            query, schema, sorting, start, size, dataset_uid=dataset, batch_uid=batch
        )

        return session.scalars(query)

    @classmethod
    def _items_query(
        cls,
        query: Select,
        schema: ItemSchema,
        dataset_uid: Optional[UUID] = None,
        batch_uid: Optional[UUID] = None,
        identifier_filter: Optional[str] = None,
        attributes_filters: Optional[Dict[str, str]] = None,
        relation_filters: Optional[Iterable[RelationFilter]] = None,
        tag_filter: Optional[Iterable[UUID]] = None,
        status_filter: Optional[Iterable[ImageStatus]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> Select:

        query = query.filter_by(schema_uid=schema.uid)
        if dataset_uid is not None:
            query = query.filter_by(dataset_uid=dataset_uid)
        if batch_uid is not None:
            query = query.filter_by(batch_uid=batch_uid)
        if identifier_filter is not None:
            query = query.filter(DatabaseItem.identifier.icontains(identifier_filter))
        if attributes_filters is not None:
            for tag, value in attributes_filters.items():
                query = query.filter(
                    DatabaseItem.attributes.any(
                        and_(
                            DatabaseAttribute.display_value.icontains(value),
                            DatabaseAttribute.tag == tag,
                        )
                    ),
                )
        if tag_filter is not None:
            for tag in tag_filter:
                query = query.filter(DatabaseItem.tags.any(DatabaseTag.uid == tag))
        if relation_filters is not None:
            for relation_filter in relation_filters:
                query = cls._relation_filter(
                    query,
                    schema,
                    relation_filter=relation_filter,
                    dataset_uid=dataset_uid,
                    batch_uid=batch_uid,
                )
        if status_filter is not None:
            query = query.filter(DatabaseImage.status.in_(status_filter))
        if selected is not None:
            query = query.filter_by(selected=selected)
        if valid is not None:
            query = query.filter_by(valid=valid)
        return query

    @classmethod
    def _relation_filter(
        cls,
        query: Select,
        schema: ItemSchema,
        relation_filter: RelationFilter,
        dataset_uid: Optional[UUID] = None,
        batch_uid: Optional[UUID] = None,
    ):
        if isinstance(schema, SampleSchema):
            if relation_filter.relation_type == RelationFilterType.PARENT:
                return cls._many_to_many_relation_filter(
                    query,
                    filtered_type=DatabaseSample,
                    counted_type=aliased(DatabaseSample),
                    table=DatabaseSample.sample_to_sample,
                    group_by=DatabaseSample.sample_to_sample.c.child_uid,
                    count_by=DatabaseSample.sample_to_sample.c.parent_uid,
                    relation_filter=relation_filter,
                    dataset_uid=dataset_uid,
                    batch_uid=batch_uid,
                )
            if relation_filter.relation_type == RelationFilterType.CHILD:
                return cls._many_to_many_relation_filter(
                    query,
                    filtered_type=DatabaseSample,
                    counted_type=aliased(DatabaseSample),
                    table=DatabaseSample.sample_to_sample,
                    group_by=DatabaseSample.sample_to_sample.c.parent_uid,
                    count_by=DatabaseSample.sample_to_sample.c.child_uid,
                    relation_filter=relation_filter,
                    dataset_uid=dataset_uid,
                    batch_uid=batch_uid,
                )
            if relation_filter.relation_type == RelationFilterType.IMAGE:
                return cls._many_to_many_relation_filter(
                    query,
                    filtered_type=DatabaseSample,
                    counted_type=DatabaseImage,
                    table=DatabaseImage.sample_to_image,
                    group_by=DatabaseImage.sample_to_image.c.image_uid,
                    count_by=DatabaseImage.sample_to_image.c.sample_uid,
                    relation_filter=relation_filter,
                    dataset_uid=dataset_uid,
                    batch_uid=batch_uid,
                )
            if relation_filter.relation_type == RelationFilterType.OBSERVATION:
                return cls._one_to_many_relation_filter(
                    query,
                    filtered_type=DatabaseSample,
                    counted_type=DatabaseObservation,
                    group_by=DatabaseObservation.sample_uid,
                    relation_filter=relation_filter,
                    dataset_uid=dataset_uid,
                    batch_uid=batch_uid,
                )

        elif isinstance(schema, ImageSchema):
            if relation_filter.relation_type == RelationFilterType.SAMPLE:
                return cls._many_to_many_relation_filter(
                    query,
                    filtered_type=DatabaseImage,
                    counted_type=DatabaseSample,
                    table=DatabaseImage.sample_to_image,
                    group_by=DatabaseImage.sample_to_image.c.image_uid,
                    count_by=DatabaseImage.sample_to_image.c.sample_uid,
                    relation_filter=relation_filter,
                    dataset_uid=dataset_uid,
                    batch_uid=batch_uid,
                )
            if relation_filter.relation_type == RelationFilterType.OBSERVATION:
                return cls._one_to_many_relation_filter(
                    query,
                    filtered_type=DatabaseImage,
                    counted_type=DatabaseObservation,
                    group_by=DatabaseObservation.image_uid,
                    relation_filter=relation_filter,
                    dataset_uid=dataset_uid,
                    batch_uid=batch_uid,
                )
            if relation_filter.relation_type == RelationFilterType.ANNOTATION:
                return cls._one_to_many_relation_filter(
                    query,
                    filtered_type=DatabaseImage,
                    counted_type=DatabaseAnnotation,
                    group_by=DatabaseAnnotation.image_uid,
                    relation_filter=relation_filter,
                    dataset_uid=dataset_uid,
                    batch_uid=batch_uid,
                )
        elif isinstance(schema, AnnotationSchema):
            if relation_filter.relation_type == RelationFilterType.IMAGE:
                return cls._many_to_one_relation_filter(
                    query,
                    filtered_type=DatabaseAnnotation,
                    counted_type=DatabaseImage,
                    join_by=DatabaseAnnotation.image_uid,
                    relation_filter=relation_filter,
                    dataset_uid=dataset_uid,
                    batch_uid=batch_uid,
                )
            if relation_filter.relation_type == RelationFilterType.OBSERVATION:
                return cls._one_to_many_relation_filter(
                    query,
                    filtered_type=DatabaseAnnotation,
                    counted_type=DatabaseObservation,
                    group_by=DatabaseObservation.annotation_uid,
                    relation_filter=relation_filter,
                    dataset_uid=dataset_uid,
                    batch_uid=batch_uid,
                )
        elif isinstance(schema, ObservationSchema):
            if relation_filter.relation_type == RelationFilterType.SAMPLE:
                return cls._many_to_one_relation_filter(
                    query,
                    filtered_type=DatabaseObservation,
                    counted_type=DatabaseSample,
                    join_by=DatabaseObservation.sample_uid,
                    relation_filter=relation_filter,
                    dataset_uid=dataset_uid,
                    batch_uid=batch_uid,
                )
            if relation_filter.relation_type == RelationFilterType.IMAGE:
                return cls._many_to_one_relation_filter(
                    query,
                    filtered_type=DatabaseObservation,
                    counted_type=DatabaseImage,
                    join_by=DatabaseObservation.image_uid,
                    relation_filter=relation_filter,
                    dataset_uid=dataset_uid,
                    batch_uid=batch_uid,
                )
            if relation_filter.relation_type == RelationFilterType.ANNOTATION:
                return cls._many_to_one_relation_filter(
                    query,
                    filtered_type=DatabaseObservation,
                    counted_type=DatabaseAnnotation,
                    join_by=DatabaseObservation.annotation_uid,
                    relation_filter=relation_filter,
                    dataset_uid=dataset_uid,
                    batch_uid=batch_uid,
                )

        raise NotImplementedError(
            f"Got unknown relation filter type {relation_filter.relation_type} for schema {schema.uid}."
        )

    @classmethod
    def _relation_sort_subquery(
        cls,
        query: Select,
        sort_query: Select,
        sorted_type: Type[DatabaseItem],
        counted_type: Type[DatabaseItem],
        group_by: Union[Column, InstrumentedAttribute],
        relation_sort: RelationSort,
        dataset_uid: Optional[UUID] = None,
        batch_uid: Optional[UUID] = None,
    ):
        subquery = cls._relation_subquery(
            sort_query,
            counted_type=counted_type,
            group_by=group_by,
            relation_schema_uid=relation_sort.relation_schema_uid,
            dataset_uid=dataset_uid,
            batch_uid=batch_uid,
        ).subquery()
        sort_by = func.coalesce(subquery.c.count, 0).label(
            f"{relation_sort.relation_schema_uid}_count"
        )
        return (
            query.add_columns(sort_by).outerjoin(
                subquery, sorted_type.uid == subquery.c.group_by
            ),
            sort_by,
        )

    @classmethod
    def _many_to_one_relation_sort(
        cls,
        query: Select,
        sorted_type: Type[DatabaseItem],
        counted_type: Type[DatabaseItem],
        join_by: InstrumentedAttribute,
        relation_sort: RelationSort,
        dataset_uid: Optional[UUID] = None,
        batch_uid: Optional[UUID] = None,
    ) -> Tuple[Select, Label]:
        sort_query = select(
            sorted_type.uid.label("group_by"),
            func.count(counted_type.uid).label("count"),
        )
        return cls._relation_sort_subquery(
            query,
            sort_query,
            sorted_type=sorted_type,
            counted_type=counted_type,
            group_by=join_by,
            relation_sort=relation_sort,
            dataset_uid=dataset_uid,
            batch_uid=batch_uid,
        )

    @classmethod
    def _one_to_many_relation_sort(
        cls,
        query: Select,
        sorted_type: Type[DatabaseItem],
        counted_type: Type[DatabaseItem],
        group_by: InstrumentedAttribute,
        relation_sort: RelationSort,
        dataset_uid: Optional[UUID] = None,
        batch_uid: Optional[UUID] = None,
    ) -> Tuple[Select, Label]:
        sort_query = select(
            group_by.label("group_by"), func.count(counted_type.uid).label("count")
        )
        return cls._relation_sort_subquery(
            query,
            sort_query,
            sorted_type=sorted_type,
            counted_type=counted_type,
            group_by=group_by,
            relation_sort=relation_sort,
            dataset_uid=dataset_uid,
            batch_uid=batch_uid,
        )

    @classmethod
    def _many_to_many_relation_sort(
        cls,
        query: Select,
        sorted_type: Type[DatabaseItem],
        counted_type: Type[DatabaseItem],
        table: Table,
        group_by: Column,
        count_by: Column,
        relation_sort: RelationSort,
        dataset_uid: Optional[UUID] = None,
        batch_uid: Optional[UUID] = None,
    ) -> Tuple[Select, Label]:
        sort_query = select(
            group_by.label("group_by"), func.count(count_by).label("count")
        ).select_from(table.join(counted_type, count_by == counted_type.uid))
        return cls._relation_sort_subquery(
            query,
            sort_query,
            sorted_type=sorted_type,
            counted_type=counted_type,
            group_by=group_by,
            relation_sort=relation_sort,
            dataset_uid=dataset_uid,
            batch_uid=batch_uid,
        )

    @classmethod
    def _many_to_many_relation_filter(
        cls,
        query: Select,
        filtered_type: Type[DatabaseItem],
        counted_type: Type[DatabaseItem],
        table: Table,
        group_by: Column,
        count_by: Column,
        relation_filter: RelationFilter,
        dataset_uid: Optional[UUID] = None,
        batch_uid: Optional[UUID] = None,
    ) -> Select:
        filter_query = select(group_by).select_from(
            table.join(counted_type, count_by == counted_type.uid)
        )
        return cls._relation_filter_subquery(
            query,
            filter_query,
            filtered_type=filtered_type,
            counted_type=counted_type,
            group_by=group_by,
            count_by=count_by,
            relation_filter=relation_filter,
            dataset_uid=dataset_uid,
            batch_uid=batch_uid,
        )

    @classmethod
    def _one_to_many_relation_filter(
        cls,
        query: Select,
        filtered_type: Type[DatabaseItem],
        counted_type: Type[DatabaseItem],
        group_by: InstrumentedAttribute,
        relation_filter: RelationFilter,
        dataset_uid: Optional[UUID] = None,
        batch_uid: Optional[UUID] = None,
    ) -> Select:
        filter_query = select(group_by).join(
            counted_type, filtered_type.uid == group_by
        )
        return cls._relation_filter_subquery(
            query,
            filter_query,
            filtered_type=filtered_type,
            counted_type=counted_type,
            group_by=group_by,
            count_by=counted_type.uid,
            relation_filter=relation_filter,
            dataset_uid=dataset_uid,
            batch_uid=batch_uid,
        )

    @classmethod
    def _many_to_one_relation_filter(
        cls,
        query: Select,
        filtered_type: Type[DatabaseItem],
        counted_type: Type[DatabaseItem],
        join_by: InstrumentedAttribute,
        relation_filter: RelationFilter,
        dataset_uid: Optional[UUID] = None,
        batch_uid: Optional[UUID] = None,
    ) -> Select:
        filter_query = select(filtered_type.uid).join(
            counted_type, counted_type.uid == join_by
        )
        return cls._relation_filter_subquery(
            query,
            filter_query,
            filtered_type=filtered_type,
            counted_type=counted_type,
            group_by=filtered_type.uid,
            count_by=counted_type.uid,
            relation_filter=relation_filter,
            dataset_uid=dataset_uid,
            batch_uid=batch_uid,
        )

    @classmethod
    def _relation_filter_subquery(
        cls,
        query: Select,
        filter_query: Select,
        filtered_type: Type[DatabaseItem],
        counted_type: Type[DatabaseItem],
        group_by: Union[Column, InstrumentedAttribute],
        count_by: Union[Column, InstrumentedAttribute],
        relation_filter: RelationFilter,
        dataset_uid: Optional[UUID] = None,
        batch_uid: Optional[UUID] = None,
    ):
        filter_query = cls._relation_subquery(
            filter_query,
            counted_type,
            group_by,
            relation_filter.relation_schema_uid,
            dataset_uid=dataset_uid,
            batch_uid=batch_uid,
        )
        if relation_filter.max_count:
            filter_query = filter_query.having(
                func.count(count_by) <= relation_filter.max_count
            )
        if relation_filter.min_count:
            filter_query = filter_query.having(
                func.count(count_by) >= relation_filter.min_count
            )
        return query.filter(filtered_type.uid.in_(filter_query))

    @staticmethod
    def _relation_subquery(
        query: Select,
        counted_type: Type[DatabaseItem],
        group_by: Union[Column, InstrumentedAttribute],
        relation_schema_uid: UUID,
        dataset_uid: Optional[UUID] = None,
        batch_uid: Optional[UUID] = None,
    ):
        query = query.filter(counted_type.schema_uid == relation_schema_uid)
        query = query.group_by(group_by)
        if dataset_uid is not None:
            query = query.filter(counted_type.dataset_uid == dataset_uid)
        if batch_uid is not None:
            query = query.filter(counted_type.batch_uid == batch_uid)
        return query

    @classmethod
    def _sort_and_limit_item_query(
        cls,
        query: Select,
        schema: ItemSchema,
        sorting: Optional[Iterable[ColumnSort]] = None,
        start: Optional[int] = None,
        size: Optional[int] = None,
        dataset_uid: Optional[UUID] = None,
        batch_uid: Optional[UUID] = None,
    ):
        if sorting is not None:
            for sort in sorting:
                if sort.sort_type == SortType.IDENTIFIER:
                    sort_by = DatabaseItem.identifier
                elif sort.sort_type == SortType.VALID:
                    sort_by = DatabaseItem.valid
                elif sort.sort_type == SortType.STATUS:
                    sort_by = DatabaseImage.status
                elif sort.sort_type == SortType.MESSAGE:
                    sort_by = DatabaseImage.status_message
                elif isinstance(sort, AttributeSort):
                    sort_by = DatabaseAttribute.display_value
                    query = query.join(
                        DatabaseAttribute,
                        DatabaseAttribute.attribute_item_uid == DatabaseItem.uid,
                    ).where(DatabaseAttribute.tag == sort.column)
                elif isinstance(sort, RelationSort):
                    query, sort_by = cls._relation_sort(
                        query,
                        schema,
                        sort,
                        dataset_uid=dataset_uid,
                        batch_uid=batch_uid,
                    )
                else:
                    raise NotImplementedError(
                        f"Got unknown sort type {sort.sort_type}."
                    )

                if sort.descending:
                    sort_by = sort_by.desc()
                query = query.order_by(sort_by)

        if start is not None:
            query = query.offset(start)
        if size is not None:
            query = query.limit(size)
        return query

    @classmethod
    def _relation_sort(
        cls,
        query: Select,
        schema: ItemSchema,
        relation_sort: RelationSort,
        dataset_uid: Optional[UUID] = None,
        batch_uid: Optional[UUID] = None,
    ) -> Tuple[Select, Label]:
        if isinstance(schema, SampleSchema):
            if relation_sort.relation_type == RelationFilterType.PARENT:
                return cls._many_to_many_relation_sort(
                    query,
                    DatabaseSample,
                    aliased(DatabaseSample),
                    DatabaseSample.sample_to_sample,
                    DatabaseSample.sample_to_sample.c.child_uid,
                    DatabaseSample.sample_to_sample.c.parent_uid,
                    relation_sort,
                    dataset_uid=dataset_uid,
                    batch_uid=batch_uid,
                )
            if relation_sort.relation_type == RelationFilterType.CHILD:
                return cls._many_to_many_relation_sort(
                    query,
                    DatabaseSample,
                    aliased(DatabaseSample),
                    DatabaseSample.sample_to_sample,
                    DatabaseSample.sample_to_sample.c.parent_uid,
                    DatabaseSample.sample_to_sample.c.child_uid,
                    relation_sort,
                    dataset_uid=dataset_uid,
                    batch_uid=batch_uid,
                )
            if relation_sort.relation_type == RelationFilterType.IMAGE:
                return cls._many_to_many_relation_sort(
                    query,
                    DatabaseSample,
                    DatabaseImage,
                    DatabaseImage.sample_to_image,
                    DatabaseImage.sample_to_image.c.image_uid,
                    DatabaseImage.sample_to_image.c.sample_uid,
                    relation_sort,
                    dataset_uid=dataset_uid,
                    batch_uid=batch_uid,
                )
            if relation_sort.relation_type == RelationFilterType.OBSERVATION:
                return cls._one_to_many_relation_sort(
                    query,
                    DatabaseSample,
                    DatabaseObservation,
                    DatabaseObservation.sample_uid,
                    relation_sort,
                    dataset_uid=dataset_uid,
                    batch_uid=batch_uid,
                )

        elif isinstance(schema, ImageSchema):
            if relation_sort.relation_type == RelationFilterType.SAMPLE:
                return cls._many_to_many_relation_sort(
                    query,
                    DatabaseImage,
                    DatabaseSample,
                    DatabaseImage.sample_to_image,
                    DatabaseImage.sample_to_image.c.image_uid,
                    DatabaseImage.sample_to_image.c.sample_uid,
                    relation_sort,
                    dataset_uid=dataset_uid,
                    batch_uid=batch_uid,
                )
            if relation_sort.relation_type == RelationFilterType.OBSERVATION:
                return cls._one_to_many_relation_sort(
                    query,
                    DatabaseImage,
                    DatabaseObservation,
                    DatabaseObservation.image_uid,
                    relation_sort,
                    dataset_uid=dataset_uid,
                    batch_uid=batch_uid,
                )
            if relation_sort.relation_type == RelationFilterType.ANNOTATION:
                return cls._one_to_many_relation_sort(
                    query,
                    DatabaseImage,
                    DatabaseAnnotation,
                    DatabaseAnnotation.image_uid,
                    relation_sort,
                    dataset_uid=dataset_uid,
                    batch_uid=batch_uid,
                )
        elif isinstance(schema, AnnotationSchema):
            if relation_sort.relation_type == RelationFilterType.IMAGE:
                return cls._many_to_one_relation_sort(
                    query,
                    DatabaseAnnotation,
                    DatabaseImage,
                    DatabaseAnnotation.image_uid,
                    relation_sort,
                    dataset_uid=dataset_uid,
                    batch_uid=batch_uid,
                )
            if relation_sort.relation_type == RelationFilterType.OBSERVATION:
                return cls._many_to_one_relation_sort(
                    query,
                    DatabaseAnnotation,
                    DatabaseObservation,
                    DatabaseObservation.annotation_uid,
                    relation_sort,
                    dataset_uid=dataset_uid,
                    batch_uid=batch_uid,
                )
        elif isinstance(schema, ObservationSchema):
            if relation_sort.relation_type == RelationFilterType.SAMPLE:
                return cls._many_to_one_relation_sort(
                    query,
                    DatabaseObservation,
                    DatabaseSample,
                    DatabaseObservation.sample_uid,
                    relation_sort,
                    dataset_uid=dataset_uid,
                    batch_uid=batch_uid,
                )
            if relation_sort.relation_type == RelationFilterType.IMAGE:
                return cls._many_to_one_relation_sort(
                    query,
                    DatabaseObservation,
                    DatabaseImage,
                    DatabaseObservation.image_uid,
                    relation_sort,
                    dataset_uid=dataset_uid,
                    batch_uid=batch_uid,
                )
            if relation_sort.relation_type == RelationFilterType.ANNOTATION:
                return cls._many_to_one_relation_sort(
                    query,
                    DatabaseObservation,
                    DatabaseAnnotation,
                    DatabaseObservation.annotation_uid,
                    relation_sort,
                    dataset_uid=dataset_uid,
                    batch_uid=batch_uid,
                )

        raise NotImplementedError(
            f"Got unknown relation sort type {relation_sort.relation_type} for schema {schema.uid}."
        )

    def _add_to_session(
        self, session: Session, item: DatabaseEnitity
    ) -> DatabaseEnitity:
        session.add(item)
        return item
