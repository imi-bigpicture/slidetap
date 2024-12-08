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
  Attribute,
  BooleanAttribute,
  CodeAttribute,
  DatetimeAttribute,
  EnumAttribute,
  ListAttribute,
  MeasurementAttribute,
  NumericAttribute,
  ObjectAttribute,
  UnionAttribute
} from 'models/attribute'
import { AttributeValueType } from 'models/attribute_value_type'

import { Code } from 'models/code'
import type { Image, Item, Observation, Sample } from 'models/item'
import { ItemValueType } from 'models/item_value_type'
import { AttributeSchema, BooleanAttributeSchema, CodeAttributeSchema, DatetimeAttributeSchema, EnumAttributeSchema, ListAttributeSchema, MeasurementAttributeSchema, NumericAttributeSchema, ObjectAttributeSchema, StringAttributeSchema, UnionAttributeSchema } from 'models/schema/attribute_schema'
import { ItemRelation, ObservationToAnnotationRelation, ObservationToImageRelation, ObservationToSampleRelation } from 'models/schema/item_relation'
import type {
  AnnotationSchema,
  ImageSchema,
  ItemSchema,

  ObservationSchema,
  SampleSchema,
} from 'models/schema/item_schema'


export function isCode(object: any): object is Code {
  return object != null && 'code' in object && 'scheme' in object && 'meaning' in object
}

export function isStringAttributeSchema(schema: AttributeSchema): schema is StringAttributeSchema {
  return (
    schema.attributeValueType === AttributeValueType.STRING
  )
}

export function isDatetimeAttributeSchema (
  schema: any
): schema is DatetimeAttributeSchema {
  return (
    schema.attributeValueType === AttributeValueType.DATETIME
  )
}

export function isNumericAttributeSchema (
  schema: any
): schema is NumericAttributeSchema {
  return (
    schema.attributeValueType === AttributeValueType.NUMERIC
  )
}

export function isMeasurementAttributeSchema (
  schema: any
): schema is MeasurementAttributeSchema {
  return (
    schema.attributeValueType === AttributeValueType.MEASUREMENT
  )
}

export function isCodeAttributeSchema(schema: AttributeSchema): schema is CodeAttributeSchema {
  return (
    schema.attributeValueType === AttributeValueType.CODE
  )
}

export function isEnumAttributeSchema(schema: AttributeSchema): schema is EnumAttributeSchema {
  return (
    schema.attributeValueType === AttributeValueType.ENUM
  )
}

export function isBooleanAttributeSchema (
  schema: any
): schema is BooleanAttributeSchema {
  return (
    schema.attributeValueType === AttributeValueType.BOOLEAN
  )
}

export function isObjectAttributeSchema(schema: AttributeSchema): schema is ObjectAttributeSchema {
  return (
    schema.attributeValueType === AttributeValueType.OBJECT
  )
}

export function isListAttributeSchema(schema: AttributeSchema): schema is ListAttributeSchema {
  return (
    schema.attributeValueType === AttributeValueType.LIST
  )
}

export function isUnionAttributeSchema(schema: AttributeSchema): schema is UnionAttributeSchema {
  return (
     schema.attributeValueType === AttributeValueType.UNION
  )
}


export function isStringAttribute(attribute: any): attribute is Attribute<string> {
  return (
    attribute.attributeValueType === AttributeValueType.STRING
  )
}

export function isDatetimeAttribute(attribute: any): attribute is DatetimeAttribute {
  return (
    attribute.attributeValueType === AttributeValueType.DATETIME
  )
}

export function isNumericAttribute(attribute: any): attribute is NumericAttribute {
  return (
    attribute.attributeValueType === AttributeValueType.NUMERIC
    )
}

export function isMeasurementAttribute(attribute: any): attribute is MeasurementAttribute {
  return (
    attribute.attributeValueType === AttributeValueType.MEASUREMENT
  )
}

export function isCodeAttribute(attribute: any): attribute is CodeAttribute {
  return (
    attribute.attributeValueType === AttributeValueType.CODE

  )
}

export function isEnumAttribute(attribute: any): attribute is EnumAttribute {
  return (
    attribute.attributeValueType === AttributeValueType.ENUM

  )
}

export function isBooleanAttribute(attribute: any): attribute is BooleanAttribute {
  return (
    attribute.attributeValueType === AttributeValueType.BOOLEAN
  )
}

export function isObjectAttribute(attribute: any): attribute is ObjectAttribute {
  return (
    attribute.attributeValueType === AttributeValueType.OBJECT
  )
}

export function isListAttribute(attribute: any): attribute is ListAttribute {
  return (
   attribute.attributeValueType === AttributeValueType.LIST

  )
}

export function isUnionAttribute(attribute: any): attribute is UnionAttribute {
  return (
   attribute.attributeValueType === AttributeValueType.UNION

  )
}

export function isItem(object: any): object is Item {
  return object != null && 'itemValueType' in object
}

export function isSampleItem(object: any): object is Sample {
  return isItem(object) && object.itemValueType === ItemValueType.SAMPLE
}

export function isImageItem(object: any): object is Image {
  return isItem(object) && object.itemValueType === ItemValueType.IMAGE
}

export function isObservationItem(object: any): object is Observation {
  return isItem(object) && object.itemValueType === ItemValueType.OBSERVATION
}

export function isObservationToSampleRelation (
  object: ItemRelation
): object is ObservationToSampleRelation {
  return object != null && 'observation' in object && 'sample' in object
}

export function isObservationToAnnotationRelation (
  object: ItemRelation
): object is ObservationToAnnotationRelation {
  return object != null && 'observation' in object && 'annotation' in object
}

export function isObservationToImageRelation (
  object: ItemRelation
): object is ObservationToImageRelation {
  return object != null && 'observation' in object && 'image' in object
}



export function isItemSchema(object: any): object is ItemSchema {
  return object != null && 'schemaUid' in object && 'itemValueType' in object
}

export function isSampleSchema(object: any): object is SampleSchema {
  return (
    isItemSchema(object) &&
    object.itemValueType === ItemValueType.SAMPLE
  )
}

export function isImageSchema(object: any): object is ImageSchema {
  return (
    isItemSchema(object) &&
    object.itemValueType === ItemValueType.IMAGE
  )
}

export function isAnnotationSchema(object: any): object is AnnotationSchema {
  return (
    isItemSchema(object) &&
    object.itemValueType === ItemValueType.ANNOTATION
  )
}

export function isObservationSchema(object: any): object is ObservationSchema {
  return (
    isItemSchema(object) &&
    object.itemValueType === ItemValueType.OBSERVATION
  )
}