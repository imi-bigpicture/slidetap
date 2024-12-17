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

from sqlalchemy import Select, and_, func, select

from slidetap.database import (
    DatabaseAnnotation,
    DatabaseAttribute,
    DatabaseImage,
    DatabaseItem,
    DatabaseObservation,
    DatabaseProject,
    DatabaseSample,
    db,
)
from slidetap.model import (
    Annotation,
    AnnotationSchema,
    Attribute,
    ColumnSort,
    Image,
    ImageSchema,
    Item,
    ItemSchema,
    ItemType,
    Observation,
    ObservationSchema,
    Project,
    Sample,
    SampleSchema,
)


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

    def get_all_projects(self) -> Iterable[DatabaseProject]:
        return db.session.scalars(select(DatabaseProject))

    def get_attribute(self, attribute: Union[UUID, Attribute, DatabaseAttribute]):
        if isinstance(attribute, UUID):
            return DatabaseAttribute.get(attribute)
        elif isinstance(attribute, Attribute):
            return DatabaseAttribute.get(attribute.uid)
        return attribute

    def get_item(
        self, item: Union[UUID, ItemType, DatabaseItem[ItemType]]
    ) -> DatabaseItem[ItemType]:
        if isinstance(item, UUID):
            return DatabaseItem.get(item)
        elif isinstance(item, Item):
            return DatabaseItem.get(item.uid)
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

    def get_project_items(
        self,
        project: Union[UUID, Project, DatabaseProject],
        schema: Optional[Union[UUID, ItemSchema]] = None,
        selected: Optional[bool] = None,
    ):
        if isinstance(project, (Project, DatabaseProject)):
            project = project.uid
        if isinstance(schema, ItemSchema):
            schema = schema.uid
        query = select(DatabaseItem).where(DatabaseItem.project_uid == project)
        if schema is not None:
            query = query.filter_by(schema_uid=schema)
        if selected is not None:
            query = query.filter_by(selected=selected)
        return db.session.scalars(query)

    def get_project_images(
        self,
        project: Union[UUID, Project, DatabaseProject],
        schema: Optional[Union[UUID, ImageSchema]] = None,
        start: Optional[int] = None,
        size: Optional[int] = None,
        identifier_filter: Optional[str] = None,
        attributes_filters: Optional[Dict[str, str]] = None,
        sorting: Optional[Iterable[ColumnSort]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> Iterable[DatabaseImage]:
        query = self._query_items_for_project_and_schema(
            select(DatabaseImage),
            project=project,
            schema=schema,
            identifier_filter=identifier_filter,
            attributes_filters=attributes_filters,
            selected=selected,
            valid=valid,
        )
        query = self._sort_and_limit_item_query(query, sorting, start, size)
        return db.session.scalars(query)

    def get_project_samples(
        self,
        project: Union[UUID, Project, DatabaseProject],
        schema: Optional[Union[UUID, SampleSchema]] = None,
        start: Optional[int] = None,
        size: Optional[int] = None,
        identifier_filter: Optional[str] = None,
        attributes_filters: Optional[Dict[str, str]] = None,
        sorting: Optional[Iterable[ColumnSort]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> Iterable[DatabaseSample]:
        query = self._query_items_for_project_and_schema(
            select(DatabaseSample),
            project=project,
            schema=schema,
            identifier_filter=identifier_filter,
            attributes_filters=attributes_filters,
            selected=selected,
            valid=valid,
        )
        query = self._sort_and_limit_item_query(query, sorting, start, size)
        return db.session.scalars(query)

    def get_project_observations(
        self,
        project: Union[UUID, Project, DatabaseProject],
        schema: Optional[Union[UUID, ObservationSchema]] = None,
        start: Optional[int] = None,
        size: Optional[int] = None,
        identifier_filter: Optional[str] = None,
        attributes_filters: Optional[Dict[str, str]] = None,
        sorting: Optional[Iterable[ColumnSort]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> Iterable[DatabaseObservation]:
        query = self._query_items_for_project_and_schema(
            select(DatabaseObservation),
            project=project,
            schema=schema,
            identifier_filter=identifier_filter,
            attributes_filters=attributes_filters,
            selected=selected,
            valid=valid,
        )
        query = self._sort_and_limit_item_query(query, sorting, start, size)
        return db.session.scalars(query)

    def get_project_annotations(
        self,
        project: Union[UUID, Project, DatabaseProject],
        schema: Optional[Union[UUID, AnnotationSchema]] = None,
        start: Optional[int] = None,
        size: Optional[int] = None,
        identifier_filter: Optional[str] = None,
        attributes_filters: Optional[Dict[str, str]] = None,
        sorting: Optional[Iterable[ColumnSort]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> Iterable[DatabaseAnnotation]:
        query = self._query_items_for_project_and_schema(
            select(DatabaseAnnotation),
            project=project,
            schema=schema,
            identifier_filter=identifier_filter,
            attributes_filters=attributes_filters,
            selected=selected,
            valid=valid,
        )
        query = self._sort_and_limit_item_query(query, sorting, start, size)
        return db.session.scalars(query)

    def get_project_item_count(
        self,
        project: Union[UUID, Project, DatabaseProject],
        schema: Optional[Union[UUID, ItemSchema]] = None,
        identifier_filter: Optional[str] = None,
        attributes_filters: Optional[Dict[str, str]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> int:
        if isinstance(project, (Project, DatabaseProject)):
            project = project.uid
        if isinstance(schema, ItemSchema):
            schema = schema.uid
        query = self._query_items_for_project_and_schema(
            select(func.count(DatabaseItem.uid)),
            project=project,
            schema=schema,
            identifier_filter=identifier_filter,
            attributes_filters=attributes_filters,
            selected=selected,
            valid=valid,
        )
        query = self._limit_query(
            query,
            project,
            schema,
            identifier_filter,
            attributes_filters,
            selected,
            valid,
        )
        return db.session.scalars(query).one()

    def delete_project_items(
        self,
        project: Union[UUID, Project, DatabaseProject],
        schema: Union[UUID, ItemSchema],
        only_non_selected=False,
    ):
        if isinstance(project, (Project, DatabaseProject)):
            project = project.uid
        if isinstance(schema, (ItemSchema)):
            schema = schema.uid
        items = self.get_project_items(project, schema)
        for item in items:
            if only_non_selected and item.selected or item in db.session.deleted:
                continue
            db.session.delete(item)
        db.session.commit()

    @classmethod
    def _query_items_for_project_and_schema(
        cls,
        query: Select,
        project: Union[UUID, Project, "DatabaseProject"],
        schema: Optional[Union[UUID, ItemSchema]] = None,
        identifier_filter: Optional[str] = None,
        attributes_filters: Optional[Dict[str, str]] = None,
        selected: Optional[bool] = None,
        valid: Optional[bool] = None,
    ) -> Select:
        if isinstance(project, (DatabaseProject, Project)):
            project = project.uid
        if isinstance(schema, ItemSchema):
            schema = schema.uid
        return cls._limit_query(
            query,
            project,
            schema,
            identifier_filter,
            attributes_filters,
            selected,
            valid,
        )

    @staticmethod
    def _limit_query(
        query: Select,
        project_uid: UUID,
        schema_uid: Optional[UUID],
        identifier_filter: Optional[str],
        attributes_filters: Optional[Dict[str, str]],
        selected: Optional[bool],
        valid: Optional[bool],
    ):
        query = query.filter_by(project_uid=project_uid)
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
