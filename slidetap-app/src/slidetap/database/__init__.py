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

"""Module containing entities stored in database."""
from slidetap.database.attribute import (
    DatabaseAttribute,
    DatabaseBooleanAttribute,
    DatabaseCodeAttribute,
    DatabaseDatetimeAttribute,
    DatabaseEnumAttribute,
    DatabaseListAttribute,
    DatabaseMeasurementAttribute,
    DatabaseNumericAttribute,
    DatabaseObjectAttribute,
    DatabaseStringAttribute,
    DatabaseUnionAttribute,
)
from slidetap.database.db import Base, NotAllowedActionError, NotFoundError
from slidetap.database.item import (
    DatabaseAnnotation,
    DatabaseImage,
    DatabaseImageFile,
    DatabaseItem,
    DatabaseItemType,
    DatabaseObservation,
    DatabaseSample,
)
from slidetap.database.mapper import (
    DatabaseMapper,
    DatabaseMapperGroup,
    DatabaseMappingItem,
)
from slidetap.database.project import (
    DatabaseBatch,
    DatabaseDataset,
    DatabaseProject,
)

__all__ = [
    "Base",
    "NotFoundError",
    "NotAllowedActionError",
    "DatabaseItem",
    "DatabaseItemType",
    "DatabaseImage",
    "DatabaseImageFile",
    "DatabaseAnnotation",
    "DatabaseObservation",
    "DatabaseSample",
    "DatabaseAttribute",
    "DatabaseStringAttribute",
    "DatabaseDatetimeAttribute",
    "DatabaseNumericAttribute",
    "DatabaseMeasurementAttribute",
    "DatabaseCodeAttribute",
    "DatabaseEnumAttribute",
    "DatabaseBooleanAttribute",
    "DatabaseObjectAttribute",
    "DatabaseListAttribute",
    "DatabaseUnionAttribute",
    "DatabaseMapper",
    "DatabaseMappingItem",
    "DatabaseMapperGroup",
    "DatabaseProject",
    "DatabaseDataset",
    "DatabaseBatch",
]
