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

import type { AttributeValueLayout } from 'src/models/schema/attribute_value_layout'

/** What the images of a group are put in order by. */
export enum ImageOrder {
  Identifier = 'identifier',
  Name = 'name',
}

/** An attribute to show with an image, and where to read it from. */
export interface ImageAttributeLayout extends AttributeValueLayout {
  /** Whose attribute this is. The image's own when null; otherwise the nearest
   * item of that kind above it — the stain is recorded on the slide a whole
   * slide image was scanned from. */
  schemaUid: string | null
}

/**
 * What was scanned under one kind of item, as pictures.
 *
 * Named attributes rather than whatever an image carries: a thumbnail has room
 * for an identifier and a word or two beside it.
 */
export interface ImagesLayout {
  uid: string
  name: string
  displayName: string
  /** Schema of the item the images are shown for. */
  schemaUid: string
  /** What to gather the images under. */
  groupBySchemaUid: string
  /** What to show on a group beside its identifier, in the order given. */
  groupAttributes: AttributeValueLayout[]
  /** Which images to show. All of them when empty. */
  imageSchemaUids: string[]
  /** What names a group, in the order given: the item of each kind at or above
   * it, by its name where it has one. Its identifier when empty. */
  groupNameSchemaUids: string[]
  /** What to show on an image beside its identifier, in the order given. */
  imageAttributes: ImageAttributeLayout[]
  /** What the images of a group are put in order by. */
  imageOrder: ImageOrder
}
