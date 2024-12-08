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

"""
Module containing schema classes used to define how metadata-schemas is represented in
the database.
"""
from slidetap.database.schema.attribute_schema import (
    AttributeValueType,
    DatabaseAttributeSchema,
    DatabaseAttributeSchemaType,
    DatabaseBooleanAttributeSchema,
    DatabaseCodeAttributeSchema,
    DatabaseDatetimeAttributeSchema,
    DatabaseEnumAttributeSchema,
    DatabaseListAttributeSchema,
    DatabaseMeasurementAttributeSchema,
    DatabaseNumericAttributeSchema,
    DatabaseObjectAttributeSchema,
    DatabaseStringAttributeSchema,
    DatabaseUnionAttributeSchema,
)
from slidetap.database.schema.item_schema import (
    DatabaseAnnotationSchema,
    DatabaseImageSchema,
    DatabaseItemSchema,
    DatabaseObservationSchema,
    DatabaseSampleSchema,
    ItemValueType,
)
from slidetap.database.schema.project_schema import DatabaseProjectSchema
from slidetap.database.schema.root_schema import DatabaseRootSchema
