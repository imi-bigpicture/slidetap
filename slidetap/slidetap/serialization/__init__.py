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
from slidetap.serialization.common import AttributeSimplifiedModel
from slidetap.serialization.dzi import DziModel
from slidetap.serialization.item import (
    AnnotationDetailsModel,
    AnnotationModel,
    ImageDetailsModel,
    ImageModel,
    ItemModelFactory,
    ObservationDetailsModel,
    ObservationModel,
    SampleDetailsModel,
    SampleModel,
)
from slidetap.serialization.mapper import (
    MapperModel,
    MapperSimplifiedModel,
    MappingItemModel,
)
from slidetap.serialization.project import ProjectModel, ProjectSimplifiedModel
from slidetap.serialization.schema import AttributeSchemaModel
