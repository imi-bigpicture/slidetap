//    Copyright 2024 SECTRA AB
//
//    Licensed under the Apache License, Version 2.0 (the "License");
//    you may not use this file except in compliance with the License.
//    You may obtain a copy of the License at
//
//        http://www.apache.org/licenses/LICENSE-2.0
//
//    Unless required by applicable law or agreed to in writing, software
//    distributed under the License is distributed on an "AS IS" BASIS,
//    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//    See the License for the specific language governing permissions and
//    limitations under the License.

import { AttributeValueType } from 'src/models/attribute_value_type'
import { Code } from 'src/models/code'
import { Measurement } from 'src/models/measurement'

export type AttributeValueTypes = string | number | Date | Measurement | Code | boolean | Record<string, Attribute<AttributeValueTypes>> | Array<Attribute<AttributeValueTypes>> | Attribute<AttributeValueTypes>

export interface Attribute<valueType> {
  /** Id of attribute. */
  uid: string
  /** Schema of attribute. */
  schemaUid: string
  /** Value of attribute. */
  originalValue?: valueType
  /** User set value of attribute. */
  updatedValue?: valueType
  /** Mapping set value of attribute*/
  mappedValue?: valueType
  /** If the attribute has a valid value set. */
  valid: boolean
  /** Display value of attribute, should summarize the attribute. */
  displayValue: string
  /** Value that can be used to map the attribute, if any. */
  mappableValue?: string
  /** Id of mapping item if present. */
  mappingItemUid?: string
  /**Type of the attribute */
  attributeValueType: AttributeValueType

}

export interface StringAttribute extends Attribute<string> {
  attributeValueType: AttributeValueType.STRING

}

export interface DatetimeAttribute extends Attribute<Date> {
  attributeValueType: AttributeValueType.DATETIME
}

export interface NumericAttribute extends Attribute<number> {
  attributeValueType: AttributeValueType.NUMERIC

}

export interface MeasurementAttribute
  extends Attribute<Measurement> {
    attributeValueType: AttributeValueType.MEASUREMENT
  }

export interface CodeAttribute extends Attribute<Code> {
  attributeValueType: AttributeValueType.CODE
}

export interface EnumAttribute extends Attribute<string> {
  attributeValueType: AttributeValueType.ENUM
}

export interface BooleanAttribute extends Attribute<boolean> {
  attributeValueType: AttributeValueType.BOOLEAN
}

export interface ObjectAttribute
  extends Attribute<Record<string, Attribute<AttributeValueTypes>>> {
    attributeValueType: AttributeValueType.OBJECT
  }

export interface ListAttribute
  extends Attribute<Array<Attribute<AttributeValueTypes>>> {
    attributeValueType: AttributeValueType.LIST
  }

export interface UnionAttribute
  extends Attribute<Attribute<AttributeValueTypes>> {
    attributeValueType: AttributeValueType.UNION
  }
