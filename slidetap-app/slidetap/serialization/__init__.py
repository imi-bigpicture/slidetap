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

"""Module containing models for serialization of entities for web client."""

from slidetap.serialization.attribute import AttributeModel
from slidetap.serialization.basic_auth import BasicAuthModel
from slidetap.serialization.batch import BatchModel
from slidetap.serialization.common import ItemReferenceModel
from slidetap.serialization.dataset import DatasetModel
from slidetap.serialization.dzi import DziModel
from slidetap.serialization.item import (
    AnnotationModel,
    ImageModel,
    ItemModel,
    ObservationModel,
    SampleModel,
)
from slidetap.serialization.mapper import (
    MapperModel,
    MappingItemModel,
)
from slidetap.serialization.project import ProjectModel
from slidetap.serialization.schema.attribute_schema import AttributeSchemaModel
from slidetap.serialization.schema.dataet_schema import DatasetSchemaModel
from slidetap.serialization.schema.item_schema import (
    ItemSchemaModel,
)
from slidetap.serialization.schema.root_schema import RootSchemaModel
from slidetap.serialization.table import TableRequestModel
from slidetap.serialization.validation import (
    BatchValidationModel,
    ProjectValidationModel,
)
