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



export interface ItemSchemaReference {
  uid: string
  name: string
  displayName: string
}

export interface ItemRelation {
  uid: string
  name: string
  description?: string
}

export interface SampleToSampleRelation extends ItemRelation {
  parent: ItemSchemaReference
  child: ItemSchemaReference
  minParents?: number
  maxParents?: number
  minChildren?: number
  maxChildren?: number
}

export interface ImageToSampleRelation extends ItemRelation {
    image: ItemSchemaReference
    sample: ItemSchemaReference
}

export interface AnnotationToImageRelation extends ItemRelation {
    annotation: ItemSchemaReference
    image: ItemSchemaReference
}

export interface ObservationToSampleRelation extends ItemRelation {
    observation: ItemSchemaReference
    sample: ItemSchemaReference
  }

export interface ObservationToImageRelation extends ItemRelation {
  observation: ItemSchemaReference
  image: ItemSchemaReference
}

export interface ObservationToAnnotationRelation extends ItemRelation {
  observation: ItemSchemaReference
  annotation: ItemSchemaReference
}
