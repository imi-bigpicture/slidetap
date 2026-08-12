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

import type { Breakpoint } from 'src/models/schema/attribute_schema'
import type { HierarchyLayout } from 'src/models/schema/hierarchy_layout'
import type { OverviewLayout } from 'src/models/schema/overview_layout'

/** What every panel of a tab has, whatever it shows. */
interface ReviewPanelLayout {
  /** How much of the tab the panel takes, out of twelve. The panels that do
   * not say divide what the rest leave. */
  width: Partial<Record<Breakpoint, number>> | null
}

export interface OverviewPanelLayout extends ReviewPanelLayout {
  kind: 'overview'
  layout: OverviewLayout
}

export interface HierarchyPanelLayout extends ReviewPanelLayout {
  kind: 'hierarchy'
  layout: HierarchyLayout
}

export interface ImagesPanelLayout extends ReviewPanelLayout {
  kind: 'images'
  /** What to group the images by. */
  groupBySchemaUid: string
  /** Which images to show. All of them when empty. */
  imageSchemaUids: string[]
}

export type AnyReviewPanelLayout =
  OverviewPanelLayout | HierarchyPanelLayout | ImagesPanelLayout

/**
 * One tab of the review view, and what it puts side by side.
 *
 * Panels rather than a single view: a tree is read against the report it was
 * made from, and images against what the laboratory says is on them.
 */
export interface ReviewTabLayout {
  /** What to call the tab. Taken from its first panel when null. */
  displayName: string | null
  panels: AnyReviewPanelLayout[]
}

/**
 * What a reviewer is shown of an item, tab by tab.
 *
 * The tabs are listed rather than gathered from the layouts that exist, so
 * that their order is a decision and a layout can be shown beside another
 * without becoming a tab of its own.
 */
export interface ReviewLayout {
  uid: string
  name: string
  /** Schema of the item being reviewed. */
  schemaUid: string
  tabs: ReviewTabLayout[]
}
