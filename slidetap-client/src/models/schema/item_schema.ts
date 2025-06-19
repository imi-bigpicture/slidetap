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

import { ItemValueType } from "src/models/item_value_type"
import { AttributeSchema } from "src/models/schema/attribute_schema"
import { AnnotationToImageRelation, ImageToSampleRelation, ObservationToAnnotationRelation, ObservationToImageRelation, ObservationToSampleRelation, SampleToSampleRelation } from "./item_relation"

export interface ItemSchema{
  uid: string
  name: string
  displayName: string
  displayOrder: number
  attributes: Record<string, AttributeSchema>
  privateAttributes: Record<string, AttributeSchema>
  itemValueType: ItemValueType
}

export interface ObservationSchema extends ItemSchema{
  samples: ObservationToSampleRelation[]
  images: ObservationToImageRelation[]
  annotations: ObservationToAnnotationRelation[]
}

export interface AnnotationSchema extends ItemSchema{
  images: AnnotationToImageRelation[]
  observations: ObservationToAnnotationRelation[]

}

export interface ImageSchema extends ItemSchema{
  samples: ImageToSampleRelation[]
  annotations: AnnotationToImageRelation[]
  observations: ObservationToImageRelation[]
}

export interface SampleSchema extends ItemSchema{
  children: SampleToSampleRelation[]
  parents: SampleToSampleRelation[]
  images: ImageToSampleRelation[]
  observations: ObservationToSampleRelation[]
}

