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

import type { Attribute, AttributeValueTypes } from 'src/models/attribute'
import { ItemValueType } from 'src/models/item_value_type'

/** One item in the tree under a root, with whatever hangs under it. */
export interface HierarchyNode {
  uid: string
  identifier: string
  /** What the item is called under its parent, where an importer set one. */
  name: string | null
  pseudonym: string | null
  schemaUid: string
  schemaDisplayName: string
  itemValueType: ItemValueType
  valid: boolean
  /** Reached through an orphan relation, so it is here for want of anywhere
   * better. */
  orphan: boolean
  /** The attributes the layout asks for, in the order it asks for them. */
  attributes: Record<string, Attribute<AttributeValueTypes>>
  children: HierarchyNode[]
}
