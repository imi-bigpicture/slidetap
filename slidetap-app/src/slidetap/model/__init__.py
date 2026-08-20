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

"""Module containing common models."""

from slidetap.model.attribute import (
    AnyAttribute,
    Attribute,
    AttributeType,
    BooleanAttribute,
    CodeAttribute,
    DatetimeAttribute,
    EnumAttribute,
    ListAttribute,
    MeasurementAttribute,
    NumericAttribute,
    ObjectAttribute,
    RejectedValues,
    StringAttribute,
    UnionAttribute,
    attribute_factory,
)
from slidetap.model.attribute_value_type import AttributeValueType
from slidetap.model.batch import Batch, BatchCreate
from slidetap.model.batch_status import BatchStatus
from slidetap.model.code import Code, CodeSuggestion
from slidetap.model.dataset import Dataset
from slidetap.model.datetime_value import DatetimeType
from slidetap.model.dzi import Dzi
from slidetap.model.file import File
from slidetap.model.image_status import ImageStatus
from slidetap.model.item import (
    Annotation,
    AnyItem,
    GroupedImage,
    Image,
    ImageFile,
    ImageFormat,
    ImageGroup,
    Item,
    ItemNeighbours,
    ItemType,
    MoveAttributeRequest,
    NewChildSuggestion,
    Observation,
    ReviewQueueItem,
    ReviewRequest,
    Sample,
    item_factory,
)
from slidetap.model.item_identity import ItemIdentity
from slidetap.model.item_value_type import ItemValueType
from slidetap.model.mapper import Mapper, MapperGroup, MappingItem
from slidetap.model.measurement import Measurement
from slidetap.model.metadata_import_status import MetadataImportStatus
from slidetap.model.metadata_search_item import MetadataSearchItem
from slidetap.model.metadata_search_result import (
    MetadataSearchResult,
    ReviewIssueToRaise,
)
from slidetap.model.project import Project
from slidetap.model.project_status import ProjectStatus
from slidetap.model.review_issue import ReviewIssue
from slidetap.model.review_issue_source import ReviewIssueSource
from slidetap.model.review_status import ReviewStatus
from slidetap.model.schema.attribute_schema import (
    AnyAttributeSchema,
    AttributeDisplay,
    AttributeDisplaySettings,
    AttributeGroupLayout,
    AttributeSchema,
    BooleanAttributeSchema,
    CodeAttributeSchema,
    DatetimeAttributeSchema,
    EnumAttributeSchema,
    ListAttributeSchema,
    MeasurementAttributeSchema,
    NumericAttributeSchema,
    ObjectAttributeSchema,
    StringAttributeSchema,
    UnionAttributeSchema,
)
from slidetap.model.schema.attribute_value_layout import AttributeValueLayout
from slidetap.model.schema.dataset_schema import DatasetSchema
from slidetap.model.schema.hierarchy_layout import (
    HierarchyLayout,
    HierarchyLevelLayout,
)
from slidetap.model.schema.images_layout import (
    ImageAttributeLayout,
    ImageOrder,
    ImagesLayout,
)
from slidetap.model.schema.item_relation import (
    Cardinality,
    ImageToSampleRelation,
    ItemRelation,
    ObservationRelation,
    SampleToSampleRelation,
)
from slidetap.model.schema.item_schema import (
    AnnotationSchema,
    AnnotationToImageRelation,
    AnyItemSchema,
    ImageSchema,
    ItemSchema,
    ObservationSchema,
    ObservationToAnnotationRelation,
    ObservationToImageRelation,
    ObservationToSampleRelation,
    SampleSchema,
)
from slidetap.model.schema.metadata_import_completeness import (
    MetadataImportCompleteness,
)
from slidetap.model.schema.overview_layout import OverviewLayout, OverviewSectionLayout
from slidetap.model.schema.project_schema import ProjectSchema
from slidetap.model.schema.review_layout import (
    HierarchyPanelLayout,
    ImagesPanelLayout,
    NonValidItemsPanelLayout,
    OverviewPanelLayout,
    ReviewIssuesPanelLayout,
    ReviewLayout,
    ReviewTabLayout,
)
from slidetap.model.schema.review_unit_schema import ReviewUnitSchema
from slidetap.model.schema.root_schema import RootSchema
from slidetap.model.session import UserSession
from slidetap.model.table import (
    AttributeFilter,
    AttributeValueField,
    ColumnSort,
    TableRequest,
)
from slidetap.model.validation import (
    BatchValidation,
    DatasetValidation,
    NonValidItem,
    ProjectValidation,
)

__all__ = [
    "AnyAttribute",
    "AnyItem",
    "Attribute",
    "AttributeType",
    "AttributeFilter",
    "AttributeValueField",
    "AttributeValueType",
    "AttributeSchema",
    "AnyAttributeSchema",
    "AnyItemSchema",
    "AttributeDisplay",
    "AttributeDisplaySettings",
    "AttributeGroupLayout",
    "Annotation",
    "AnnotationSchema",
    "AnnotationToImageRelation",
    "Batch",
    "BatchCreate",
    "BatchStatus",
    "BatchValidation",
    "BooleanAttribute",
    "BooleanAttributeSchema",
    "Code",
    "CodeAttribute",
    "CodeAttributeSchema",
    "CodeSuggestion",
    "ColumnSort",
    "Dataset",
    "DatasetSchema",
    "DatasetValidation",
    "DatetimeAttribute",
    "DatetimeAttributeSchema",
    "DatetimeType",
    "Dzi",
    "EnumAttribute",
    "EnumAttributeSchema",
    "File",
    "Image",
    "ImageFile",
    "ImageFormat",
    "GroupedImage",
    "ImageGroup",
    "ImageSchema",
    "ImageStatus",
    "MetadataImportCompleteness",
    "ImageToSampleRelation",
    "Item",
    "ItemIdentity",
    "ItemNeighbours",
    "NewChildSuggestion",
    "ItemRelation",
    "ItemSchema",
    "ItemType",
    "ItemValueType",
    "ListAttribute",
    "ListAttributeSchema",
    "Mapper",
    "MapperGroup",
    "MappingItem",
    "Measurement",
    "MeasurementAttribute",
    "MeasurementAttributeSchema",
    "MetadataImportStatus",
    "MetadataSearchItem",
    "MetadataSearchResult",
    "ReviewIssueToRaise",
    "MoveAttributeRequest",
    "ReviewQueueItem",
    "ReviewRequest",
    "NumericAttribute",
    "NumericAttributeSchema",
    "ObjectAttribute",
    "RejectedValues",
    "ObjectAttributeSchema",
    "Observation",
    "ObservationRelation",
    "ObservationSchema",
    "ObservationToAnnotationRelation",
    "ObservationToImageRelation",
    "ObservationToSampleRelation",
    "AttributeValueLayout",
    "ImageAttributeLayout",
    "ImageOrder",
    "ImagesLayout",
    "HierarchyLayout",
    "HierarchyLevelLayout",
    "OverviewLayout",
    "OverviewSectionLayout",
    "Project",
    "HierarchyPanelLayout",
    "ImagesPanelLayout",
    "NonValidItemsPanelLayout",
    "ReviewIssuesPanelLayout",
    "OverviewPanelLayout",
    "ProjectSchema",
    "ReviewLayout",
    "ReviewUnitSchema",
    "NonValidItem",
    "ReviewTabLayout",
    "ProjectStatus",
    "ReviewIssue",
    "ReviewIssueSource",
    "ReviewStatus",
    "ProjectValidation",
    "RootSchema",
    "Sample",
    "SampleSchema",
    "Cardinality",
    "SampleToSampleRelation",
    "StringAttribute",
    "StringAttributeSchema",
    "TableRequest",
    "UnionAttribute",
    "UnionAttributeSchema",
    "UserSession",
    "attribute_factory",
    "item_factory",
]
