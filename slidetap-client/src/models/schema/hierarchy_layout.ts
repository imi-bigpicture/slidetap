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

import { AttributeValueField } from 'src/models/table_item'

/** An attribute to show for an item, and which of its values to show. */
export interface HierarchyAttributeLayout {
  tag: string
  /** The mapped value is what the item means; the mappable one is what it was
   * given as, which is what the systems it came from show. */
  field: AttributeValueField
}

/** One kind of item in the tree, and what to say about it. */
export interface HierarchyLevelLayout {
  schemaUid: string
  /** What to show for an item of this level, in the order given. Also what the
   * tree can be searched by. */
  attributes: HierarchyAttributeLayout[]
  /** Show items of this level beside their parent rather than under it, for a
   * level that holds about one item per parent. */
  inline: boolean
  /** Whether an item of this level may be dragged onto another item. Where it
   * may be dropped comes from the relations between the schemas. */
  movable: boolean
}

/**
 * The tree under one kind of item, level by level.
 *
 * A level not named is not shown, and neither is anything under it, so the
 * layout decides both what the tree reaches and what it shows.
 */
export interface HierarchyLayout {
  uid: string
  name: string
  displayName: string
  /** Schema of the item the tree is built from. The item itself is not part of
   * the tree, only what hangs under it. */
  schemaUid: string
  levels: HierarchyLevelLayout[]
}
