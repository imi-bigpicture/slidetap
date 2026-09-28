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


import { ItemValueType } from 'src/models/item_value_type'

/** Putting an item into the project or taking it out, and how far what
 * follows it may reach. The cascade options default, server side, to
 * following everything the schema says must follow. */
export interface ItemSelect {
  select: boolean
  comment: string | null
  tags: string[] | null
  additiveTags: boolean
  /** Follow relations to what the item hangs under. */
  cascadeUp?: boolean
  /** Follow relations to what hangs under the item. */
  cascadeDown?: boolean
  /** Item schemas the cascade leaves as they are. */
  skipSchemas?: string[]
  /** When selecting, also bring back what a curator took out by name. */
  overrideCuration?: boolean
  /** Work out what would change and report it, changing nothing. */
  dryRun?: boolean
}

/** How an item came to change with the one that was asked for. */
export enum CascadeDirection {
  Item = 'item',
  Up = 'up',
  Down = 'down',
}

/** One item whose selection a request changed, or would change. */
export interface SelectionChange {
  uid: string
  identifier: string
  schemaUid: string
  itemValueType: ItemValueType
  /** Whether the item is in the project after the change. */
  selected: boolean
  direction: CascadeDirection
  /** A curator had taken the item out by name, and the change brought it
   * back because it was asked to. */
  overrodeCuration: boolean
}

/** What a selection changed, or in a dry run would change. */
export interface ItemSelectResult {
  /** Every item whose selection flipped, the named item first. */
  changed: SelectionChange[]
  /** What the cascade left out because a curator had taken it out by name. */
  keptOut: SelectionChange[]
  /** Items in the project afterwards whose relations are not satisfied. */
  leftInvalid: SelectionChange[]
  dryRun: boolean
}