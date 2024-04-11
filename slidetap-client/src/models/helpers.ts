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
  Code,
  CodeAttribute,
  DatetimeAttribute,
  EnumAttribute,
  ListAttribute,
  MeasurementAttribute,
  NumericAttribute,
  ObjectAttribute,
  StringAttribute,
  UnionAttribute,
} from './attribute'
import { AttributeValueType } from './attribute'

import type { ImageDetails, ItemDetails, ObservationDetails, SampleDetails } from './item'
import type {
  AnnotationSchema,
  AttributeSchema,
  BooleanAttributeSchema,
  CodeAttributeSchema,
  DatetimeAttributeSchema,
  EnumAttributeSchema,
  ImageSchema,
  ItemRelation,
  ItemSchema,
  ListAttributeSchema,
  MeasurementAttributeSchema,
  NumericAttributeSchema,
  ObjectAttributeSchema,
  ObservationSchema,
  ObservationToAnnotationRelation,
  ObservationToImageRelation,
  ObservationToSampleRelation,
  SampleSchema,
  StringAttributeSchema,
  UnionAttributeSchema
} from './schema'
import { ItemType } from './schema'


export function isCode(object: any): object is Code {
  return object != null && 'code' in object && 'scheme' in object && 'meaning' in object
}

export function isAttributeSchema(object: any): object is AttributeSchema {
  return object != null && 'schemaUid' in object && 'attributeValueType' in object
}

export function isStringAttributeSchema(object: any): object is StringAttributeSchema {
  return (
    isAttributeSchema(object) &&
    object.attributeValueType === AttributeValueType.STRING
  )
}

export function isDatetimeAttributeSchema (
  object: any
): object is DatetimeAttributeSchema {
  return (
    isAttributeSchema(object) &&
    object.attributeValueType === AttributeValueType.DATETIME
  )
}

export function isNumericAttributeSchema (
  object: any
): object is NumericAttributeSchema {
  return (
    isAttributeSchema(object) &&
    object.attributeValueType === AttributeValueType.NUMERIC
  )
}

export function isMeasurementAttributeSchema (
  object: any
): object is MeasurementAttributeSchema {
  return (
    isAttributeSchema(object) &&
    object.attributeValueType === AttributeValueType.MEASUREMENT
  )
}

export function isCodeAttributeSchema(object: any): object is CodeAttributeSchema {
  return (
    isAttributeSchema(object) && object.attributeValueType === AttributeValueType.CODE
  )
}

export function isEnumAttributeSchema(object: any): object is EnumAttributeSchema {
  return (
    isAttributeSchema(object) && object.attributeValueType === AttributeValueType.ENUM
  )
}

export function isBooleanAttributeSchema (
  object: any
): object is BooleanAttributeSchema {
  return (
    isAttributeSchema(object) &&
    object.attributeValueType === AttributeValueType.BOOLEAN
  )
}

export function isObjectAttributeSchema(object: any): object is ObjectAttributeSchema {
  return (
    isAttributeSchema(object) &&
    object.attributeValueType === AttributeValueType.OBJECT
  )
}

export function isListAttributeSchema(object: any): object is ListAttributeSchema {
  return (
    isAttributeSchema(object) && object.attributeValueType === AttributeValueType.LIST
  )
}

export function isUnionAttributeSchema(object: any): object is UnionAttributeSchema {
  return (
    isAttributeSchema(object) && object.attributeValueType === AttributeValueType.UNION
  )
}


export function isAttribute(object: any): object is Attribute<any, any> {
  return object != null && 'schema' in object && isAttributeSchema(object.schema)
}

export function isStringAttribute(object: any): object is StringAttribute {
  return (
    isAttribute(object) &&
    isStringAttributeSchema(object.schema)
  )
}

export function isDatetimeAttribute(object: any): object is DatetimeAttribute {
  return (
    isAttribute(object) &&
    isDatetimeAttributeSchema(object.schema)
  )
}

export function isNumericAttribute(object: any): object is NumericAttribute {
  return (
    isAttribute(object) &&
    isNumericAttributeSchema(object.schema)
    )
}

export function isMeasurementAttribute(object: any): object is MeasurementAttribute {
  return (
    isAttribute(object) &&
    isMeasurementAttributeSchema(object.schema)
  )
}

export function isCodeAttribute(object: any): object is CodeAttribute {
  return (
    isAttribute(object) && isCodeAttributeSchema(object.schema)
  )
}

export function isEnumAttribute(object: any): object is EnumAttribute {
  return (
    isAttribute(object) && isEnumAttributeSchema(object.schema)
  )
}

export function isBooleanAttribute(object: any): object is BooleanAttribute {
  return (
    isAttribute(object) &&
    isBooleanAttributeSchema(object.schema)
  )
}

export function isObjectAttribute(object: any): object is ObjectAttribute {
  return (
    isAttribute(object) &&
    isObjectAttributeSchema(object.schema)
  )
}

export function isListAttribute(object: any): object is ListAttribute {
  return (
    isAttribute(object) && isListAttributeSchema(object.schema)
  )
}

export function isUnionAttribute(object: any): object is UnionAttribute {
  return (
    isAttribute(object) && isUnionAttributeSchema(object.schema)
  )
}

export function isItem(object: any): object is ItemDetails {
  return object != null && 'itemValueType' in object
}

export function isSampleItem(object: any): object is SampleDetails {
  return isItem(object) && object.itemValueType === ItemType.SAMPLE
}

export function isImageItem(object: any): object is ImageDetails {
  return isItem(object) && object.itemValueType === ItemType.IMAGE
}

export function isObservationItem(object: any): object is ObservationDetails {
  return isItem(object) && object.itemValueType === ItemType.OBSERVATION
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
    object.itemValueType === ItemType.SAMPLE
  )
}

export function isImageSchema(object: any): object is ImageSchema {
  return (
    isItemSchema(object) &&
    object.itemValueType === ItemType.IMAGE
  )
}

export function isAnnotationSchema(object: any): object is AnnotationSchema {
  return (
    isItemSchema(object) &&
    object.itemValueType === ItemType.ANNOTATION
  )
}

export function isObservationSchema(object: any): object is ObservationSchema {
  return (
    isItemSchema(object) &&
    object.itemValueType === ItemType.OBSERVATION
  )
}