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

import type { AttributeValueType, DatetimeType } from './attribute'

export enum ItemType {
  SAMPLE = 1,
  IMAGE = 2,
  ANNOTATION = 3,
  OBSERVATION = 4,
}

export interface AttributeSchema {
  uid: string
  tag: string
  displayName: string
  attributeValueType: AttributeValueType
  displayInTable: boolean
  schemaUid: string
  optional: boolean
  readOnly: boolean
}

export interface StringAttributeSchema extends AttributeSchema {
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
  isInt: boolean
  attributeValueType: AttributeValueType.NUMERIC
}

export interface MeasurementAttributeSchema extends AttributeSchema {
  allowedUnits?: string[]
  attributeValueType: AttributeValueType.MEASUREMENT
}

export interface CodeAttributeSchema extends AttributeSchema {
  allowedSchemas?: string[]
  attributeValueType: AttributeValueType.CODE
}

export interface BooleanAttributeSchema extends AttributeSchema {
  trueDisplayValue: string
  falseDisplayValue: string
  attributeValueType: AttributeValueType.BOOLEAN
}

export interface ObjectAttributeSchema extends AttributeSchema {
  displayAttributesInParent: boolean
  attributes: AttributeSchema[]
  attributeValueType: AttributeValueType.OBJECT
}

export interface ListAttributeSchema extends AttributeSchema {
  displayAttributesInParent: boolean
  attribute: AttributeSchema
  attributeValueType: AttributeValueType.LIST
}

export interface UnionAttributeSchema extends AttributeSchema {
  attributes: AttributeSchema[]
  attributeValueType: AttributeValueType.UNION
}

export interface ProjectSchema{
  uid: string
  name: string
  attributes: AttributeSchema[]
  schemaUid: string
  displayName: string
}


export interface ItemSchema{
  uid: string
  name: string
  itemValueType: ItemType
  attributes: AttributeSchema[]
  schemaUid: string
  displayName: string
}


export interface ItemRelation {
  uid: string
  name: string
  description?: string
}

export interface SampleToSampleRelation extends ItemRelation {
  parent: ItemSchema
  child: ItemSchema
  minParents?: number
  maxParents?: number
  minChildren?: number
  maxChildren?: number
}

export interface ImageToSampleRelation extends ItemRelation {
  image: ItemSchema
  sample: ItemSchema
}

export interface AnnotationToImageRelation extends ItemRelation {
  annotation: ItemSchema
  image: ItemSchema
}

export interface ObservationRelation extends ItemRelation {
  observation: ItemSchema
}

export interface ObservationToSampleRelation extends ObservationRelation {
  sample: ItemSchema
}

export interface ObservationToImageRelation extends ObservationRelation {
  image: ItemSchema
}

export interface ObservationToAnnotationRelation extends ObservationRelation {
  annotation: ItemSchema
}

export interface SampleSchema extends ItemSchema{
  children: SampleToSampleRelation[]
  parents: SampleToSampleRelation[]
  images: ImageToSampleRelation[]
  observations: ObservationToSampleRelation[]
}

export interface ImageSchema extends ItemSchema{
  samples: ImageToSampleRelation[]
  annotations: AnnotationToImageRelation[]
  observations: ObservationToImageRelation[]
}

export interface AnnotationSchema extends ItemSchema{
  images: AnnotationToImageRelation[]
  observations: ObservationToAnnotationRelation[]

}

export interface ObservationSchema extends ItemSchema{
  samples: ObservationToSampleRelation[]
  images: ObservationToImageRelation[]
  annotations: ObservationToAnnotationRelation[]
}


export const ItemValueTypeStrings = {
  [ItemType.SAMPLE]: "Sample",
  [ItemType.IMAGE]: "Image",
  [ItemType.OBSERVATION]: "Observation",
  [ItemType.ANNOTATION]: "Annotation"
}