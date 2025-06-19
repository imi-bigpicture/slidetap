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

import { UUID } from 'crypto'
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
  datasetUid: string
  batchUid: string | null
  schemaDisplayName: string
  schemaUid: string
  itemValueType: ItemValueType
}

export interface Observation extends Item {
  item: string
  sample: string | null
  image: string | null
  annotation: string | null
  itemValueType: ItemValueType.OBSERVATION
}

export interface Annotation extends Item {
  image: string | null
  observations: string[]
  itemValueType: ItemValueType.ANNOTATION
}

export interface ImageFile {
  uid: UUID
  filename: string
}

export interface Image extends Item {
  external_identifier: string | null
  folder_path: string | null
  thumbnail_path: string | null
  status: ImageStatus
  statusMessage: string
  files: ImageFile[]
  samples: string[]
  annotations: string[]
  observations: string[]
  itemValueType: ItemValueType.IMAGE
}

export interface Sample extends Item {
  parents: string[]
  children: string[]
  images: string[]
  observations: string[]
  itemValueType: ItemValueType.SAMPLE
}

export interface ImageGroup {
  identifier: string
  name: string | null
  images: Image[]
}