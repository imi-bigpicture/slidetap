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
    Attribute,
    BooleanAttribute,
    CodeAttribute,
    DatetimeAttribute,
    EnumAttribute,
    ListAttribute,
    MeasurementAttribute,
    NumericAttribute,
    ObjectAttribute,
    StringAttribute,
    UnionAttribute,
)
from slidetap.model.attribute_value_type import AttributeValueType
from slidetap.model.batch import Batch
from slidetap.model.batch_status import BatchStatus
from slidetap.model.code import Code
from slidetap.model.dataset import Dataset
from slidetap.model.datetime_value import DatetimeType
from slidetap.model.dzi import Dzi
from slidetap.model.image_status import ImageStatus
from slidetap.model.item import (
    Annotation,
    Image,
    ImageFile,
    Item,
    ItemType,
    Observation,
    Sample,
)
from slidetap.model.item_value_type import ItemValueType
from slidetap.model.mapper import Mapper, MappingItem
from slidetap.model.measurement import Measurement
from slidetap.model.project import Project
from slidetap.model.project_status import ProjectStatus
from slidetap.model.schema.attribute_schema import (
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
from slidetap.model.schema.item_relation import (
    ImageToSampleRelation,
    ItemRelation,
    ObservationRelation,
    SampleToSampleRelation,
)
from slidetap.model.schema.item_schema import (
    AnnotationSchema,
    AnnotationToImageRelation,
    ImageSchema,
    ImageToSampleRelation,
    ItemSchema,
    ObservationSchema,
    ObservationToAnnotationRelation,
    ObservationToImageRelation,
    ObservationToSampleRelation,
    SampleSchema,
    SampleToSampleRelation,
)
from slidetap.model.schema.project_schema import DatasetSchema, ProjectSchema
from slidetap.model.schema.root_schema import RootSchema
from slidetap.model.session import UserSession
from slidetap.model.table import ColumnSort, TableRequest
from slidetap.model.validation import (
    BatchValidation,
    DatasetValidation,
    ProjectValidation,
)
