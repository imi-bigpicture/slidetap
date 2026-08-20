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
import { ReviewStatus } from './review_status'

export interface Item {
  uid: string
  identifier: string
  name: string | null
  pseudonym: string | null
  selected: boolean
  valid: boolean
  validAttributes: boolean
  validRelations: boolean
  attributes: Record<string, Attribute<AttributeValueTypes>>
  privateAttributes: Record<string, Attribute<AttributeValueTypes>>
  tags: string[]
  comment: string | null
  reviewStatus: ReviewStatus
  /** When a user last saved the item, as an ISO string. Null for one nobody
   * has edited — an import is not a save. */
  lastSaved: string | null
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

export enum ImageFormat {
  DICOM_WSI = 'DICOM_WSI',
  OTHER_WSI = 'OTHER_WSI',
  DICOM_SINGLE_FRAME = 'DICOM_SINGLE_FRAME',
  OTHER_SINGLE_FRAME = 'OTHER_SINGLE_FRAME',
}

export interface Image extends Item {
  external_identifier: string | null
  status: ImageStatus
  statusMessage: string
  processingStartedAt: string | null
  lastHeartbeatAt: string | null
  files: ImageFile[]
  samples: Record<string, string[]>
  annotations: Record<string, string[]>
  observations: Record<string, string[]>
  format: ImageFormat
  itemValueType: ItemValueType.IMAGE
}

export interface Sample extends Item {
  parents: Record<string, string[]>
  children: Record<string, string[]>
  images: Record<string, string[]>
  observations: Record<string, string[]>
  itemValueType: ItemValueType.SAMPLE
}

/** What comes before and after an item among those of its own kind. */
export interface ItemNeighbours {
  previousUid: string | null
  nextUid: string | null
}

/** An image as a gallery shows it: the image, and what to say beside it. */
export interface GroupedImage {
  image: Image
  /** What the layout asked for, in the order it asked. Read from the image or
   * from the item above it the layout named. */
  attributes: Record<string, Attribute<AttributeValueTypes>>
}

export interface ImageGroup {
  identifier: string
  name: string | null
  schemaUid: string
  /** What to call the group, as the layout names it. */
  label: string
  images: GroupedImage[]
  /** What the layout asked for of the item the group stands for. */
  attributes: Record<string, Attribute<AttributeValueTypes>>
}

/** What adding an item of a schema under another item would do: the name it
 * would be given, and the item already carrying that name where there is one.
 * Adding under a used name gives that item back rather than making another, so
 * one that has been removed from the project is restored by it. */
export interface NewChildSuggestion {
  identifier: string
  existingUid: string | null
  existingInProject: boolean
}
