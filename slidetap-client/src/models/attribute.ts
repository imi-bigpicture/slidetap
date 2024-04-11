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

import type {
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
} from './schema'
import type { ValueStatus } from './status'

export enum AttributeValueType {
  STRING = 1,
  DATETIME = 2,
  NUMERIC = 3,
  MEASUREMENT = 4,
  CODE = 5,
  ENUM = 6,
  BOOLEAN = 7,
  OBJECT = 8,
  LIST = 10,
  UNION = 11,
}

export const AttributeValueTypeStrings = {
  [AttributeValueType.STRING]: "String",
  [AttributeValueType.DATETIME]: "Datetime",
  [AttributeValueType.NUMERIC]: "Numeric",
  [AttributeValueType.MEASUREMENT]: "Measurement",
  [AttributeValueType.CODE]: "Code",
  [AttributeValueType.ENUM]: "Enum",
  [AttributeValueType.BOOLEAN]: "Boolean",
  [AttributeValueType.OBJECT]: "Object",
  [AttributeValueType.LIST]: "List",
  [AttributeValueType.UNION]: "Union"
}

export enum DatetimeType {
  TIME = 1,
  DATE = 2,
  DATETIME = 3,
}

export const DatetimeTypeStrings = {
  [DatetimeType.TIME]: "Time",
  [DatetimeType.DATE]: "Date",
  [DatetimeType.DATETIME]: "Datetime",

}

export interface Code {
  code: string
  scheme: string
  meaning: string
  schemeVersion?: string
}

export interface Measurement {
  value: number
  unit: string
}

export enum ComplexAttributeDisplayType {
  ROOT = 1,
  BUTTON = 2,
  INLINE = 3
}

export interface Attribute<valueType, AttributeSchema> {
  /** Id of attribute. */
  uid: string
  /** Schema of attribute. */
  schema: AttributeSchema
  /** Display value of attribute, should summarize the attribute. */
  displayValue: string
  /** Value that can be used to map the attribute, if any. */
  mappableValue?: string
  /** Value of attribute. */
  value?: valueType
  /** Original value of the attribute */
  originalValue?: valueType
  /** If the attribute has been mapped or not etc. */
  mappingStatus: ValueStatus
  /** If the attribute has a valid value set. */
  valid: boolean
  /** Id of mapping item if present. */
  mappingItemUid?: string
}

export interface StringAttribute extends Attribute<string, StringAttributeSchema> {}

export interface DatetimeAttribute extends Attribute<Date, DatetimeAttributeSchema> {}

export interface NumericAttribute extends Attribute<number, NumericAttributeSchema> {}

export interface MeasurementAttribute
  extends Attribute<Measurement, MeasurementAttributeSchema> {}

export interface CodeAttribute extends Attribute<Code, CodeAttributeSchema> {}

export interface EnumAttribute extends Attribute<string, EnumAttributeSchema> {}

export interface BooleanAttribute extends Attribute<boolean, BooleanAttributeSchema> {}

export interface ObjectAttribute
  extends Attribute<Record<string, Attribute<any, any>>, ObjectAttributeSchema> {}

export interface ListAttribute
  extends Attribute<Array<Attribute<any, any>>, ListAttributeSchema> {}

export interface UnionAttribute
  extends Attribute<Attribute<any, any>, UnionAttributeSchema> {}

export interface AttributeValidation {
  is_valid: boolean
}

export enum ValueDisplayType {
  CURRENT,
  ORIGINAL,
  MAPPED,
}