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

import type { Attribute, AttributeValueTypes } from './attribute'
import { ImageStatus } from './image_status'
import { ItemValueType } from './item_value_type'

export interface Item {
  uid: string
  identifier: string
  name: string | null
  pseodonym: string | null
  selected: boolean
  valid: boolean
  validAttributes: boolean
  validRelations: boolean
  attributes: Record<string, Attribute<AttributeValueTypes>>
  privateAttributes: Record<string, Attribute<AttributeValueTypes>>
  tags: string[]
  comment: string | null
  datasetUid: string
  batchUid: string | null
  schemaDisplayName: string
  schemaUid: string
  itemValueType: ItemValueType
}

export interface Observation extends Item {
  item: [string, string] | null
  sample: [string, string] | null
  image: [string, string] | null
  annotation: [string, string] | null
  itemValueType: ItemValueType.OBSERVATION
}

export interface Annotation extends Item {
  image: [string, string] | null
  observations: Record<string, string[]>
  itemValueType: ItemValueType.ANNOTATION
}

export interface ImageFile {
  uid: string
  filename: string
}

export interface Image extends Item {
  external_identifier: string | null
  folder_path: string | null
  thumbnail_path: string | null
  status: ImageStatus
  statusMessage: string
  files: ImageFile[]
  samples: Record<string, string[]>
  annotations: Record<string, string[]>
  observations: Record<string, string[]>
  itemValueType: ItemValueType.IMAGE
}

export interface Sample extends Item {
  parents: Record<string, string[]>
  children: Record<string, string[]>
  images: Record<string, string[]>
  observations: Record<string, string[]>
  itemValueType: ItemValueType.SAMPLE
}

export interface ImageGroup {
  identifier: string
  name: string | null
  images: Image[]
}