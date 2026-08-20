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
import { DatetimeType } from 'src/models/datetime_type'

export type Breakpoint = 'xs' | 'sm' | 'md' | 'lg' | 'xl'

/**
 * Where an attribute is shown. A flag rather than a boolean per place: one
 * worth a table column is not always worth a field in the detail panel, and
 * one that reads the same on every item of its schema is worth neither.
 *
 * Values are the bits the backend's `AttributeDisplay` sends.
 *
 * @example
 * if (isShown(schema, AttributeDisplay.Table)) { ...render a column... }
 */
export enum AttributeDisplay {
  None = 0,
  Table = 1,
  Details = 2,
  All = 3,
}

/** Whether a schema asks to be shown in the given place. */
export const isShown = (
  schema: Pick<AttributeSchema, 'display'>,
  where: AttributeDisplay,
): boolean => (schema.display & where) !== 0

export interface AttributeDisplaySettings {
  width: Partial<Record<Breakpoint, number>>
}

export interface AttributeGroupLayout {
  name: string | null
  expand: boolean
  width: Partial<Record<Breakpoint, number>>
  direction: 'column' | 'row'
  /** Render the group folded behind its name. */
  collapsed: boolean
  attributes: Record<string, AttributeDisplaySettings>
}

export interface AttributeSchema {
  uid: string
  tag: string
  name: string
  displayName: string
  /** Where the attribute is shown. Bits of AttributeDisplay, as sent. */
  display: AttributeDisplay
  optional: boolean
  readOnly: boolean
  description: string | null
  attributeValueType: AttributeValueType
}

export interface StringAttributeSchema extends AttributeSchema {
  multiline: boolean
  attributeValueType: AttributeValueType.STRING
}

export interface EnumAttributeSchema extends AttributeSchema {
  allowedValues: string[]
  attributeValueType: AttributeValueType.ENUM
}

export interface DatetimeAttributeSchema extends AttributeSchema {
  datetimeType: DatetimeType
  attributeValueType: AttributeValueType.DATETIME
}

export interface NumericAttributeSchema extends AttributeSchema {
  isInteger: boolean
  minValue: number | null
  maxValue: number | null
  attributeValueType: AttributeValueType.NUMERIC
}

export interface MeasurementAttributeSchema extends AttributeSchema {
  allowedUnits: string[] | null
  minValue: number | null
  maxValue: number | null
  attributeValueType: AttributeValueType.MEASUREMENT
}

export interface CodeAttributeSchema extends AttributeSchema {
  allowedSchemas: string[] | null
  attributeValueType: AttributeValueType.CODE
}

export interface BooleanAttributeSchema extends AttributeSchema {
  trueDisplayValue: string
  falseDisplayValue: string
  attributeValueType: AttributeValueType.BOOLEAN
}

export interface ObjectAttributeSchema extends AttributeSchema {
  displayAttributesInParent: boolean
  attributes: Record<string, AttributeSchema>
  attributeLayout: AttributeGroupLayout[]
  attributeValueType: AttributeValueType.OBJECT
}

export interface ListAttributeSchema extends AttributeSchema {
  displayAttributesInParent: boolean
  attribute: AttributeSchema
  minItems: number | null
  maxItems: number | null
  attributeValueType: AttributeValueType.LIST
}

export interface UnionAttributeSchema extends AttributeSchema {
  attributes: AttributeSchema[]
  attributeValueType: AttributeValueType.UNION
}
