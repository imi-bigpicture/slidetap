//    Copyright 2026 SECTRA AB
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

import type { ItemIdentity } from './item_identity'
import type { ItemGroupingPolicy } from './schema/item_grouping_policy'

/** One of what a value of a group is made of, such as one diagnose of a set
 * of them, shown as a chip. */
export interface ItemGroupValuePart {
  label: string
  /** Shown on hover, such as the code a meaning is of. */
  description: string | null
}

/** A group, with its items named. */
export interface ItemGroupSummary {
  /** What the items share, as shown, one per column of the grouping. What the
   * groups are sorted, filtered and told apart by. */
  values: string[]
  /** What each value is made of, one list per column. Empty, or empty for a
   * column, where the value is shown as its text. */
  parts: ItemGroupValuePart[][]
  items: ItemIdentity[]
  /** How many of what the policy counts the items are of, e.g. patients. Can
   * be fewer than the items: one patient can have several. */
  count: number
  /** The review units the items are answered for in, such as their cases,
   * each once. Empty where nothing above the items is reviewed. */
  reviewUnitUids: string[]
  /** Whether the group holds fewer than the policy asks for. */
  belowMinimum: boolean
}

/** An item in no group, as it lacks a value grouped by. */
export interface IncompleteGroupedItem {
  item: ItemIdentity
  /** The columns the item has no value for. */
  missing: string[]
}

/** The groups of the selected items of a project, or of one of its batches,
 * smallest first. */
export interface ItemGrouping {
  policy: ItemGroupingPolicy
  /** The batch the items are of, null where they are of the whole project. */
  batchUid: string | null
  columns: string[]
  groups: ItemGroupSummary[]
  incomplete: IncompleteGroupedItem[]
}
