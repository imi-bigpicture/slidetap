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

import { useMemo, useState } from 'react'
import type { OverviewEditState } from 'src/components/overview/overview_view'
import type { ReviewLayout, ReviewTabLayout } from 'src/models/schema/review_layout'
import type { RootSchema } from 'src/models/schema/root_schema'

/** What the editable panels of the tab shown hold unsaved, gathered so that
 * one save and revert can be drawn above them all. */
export interface PanelEdits {
  /** Where each panel of the tab, by its index, reports its edit state. */
  editReporters: Array<(state: OverviewEditState) => void>
  isDirty: boolean
  saving: boolean
  save: () => void
  revert: () => void
}

/**
 * The edit state of the panels of the tab shown, for a view that steps from
 * one unit to the next.
 *
 * Only the panels of the tab being shown count: the others are unmounted, and
 * what they last reported says nothing about what is on screen. Dropped when
 * the unit changes rather than left to be written over: the panels of the
 * next unit report as they mount, but a unit whose tabs hold no editable panel
 * reports nothing, and the buttons would go on offering to save what the last
 * one had.
 */
export function usePanelEdits(
  tabIndex: number,
  panelCount: number,
  unitUid: string | undefined,
): PanelEdits {
  const [editStates, setEditStates] = useState<Record<string, OverviewEditState>>({})
  const [shownUid, setShownUid] = useState(unitUid)
  if (unitUid !== shownUid) {
    setShownUid(unitUid)
    setEditStates({})
  }
  // One callback per panel of the tab, kept: a panel reports its edit state
  // from an effect that watches the callback, so handing it a new one every
  // render would have the report cause the render that causes the next report.
  const editReporters = useMemo(
    () =>
      Array.from({ length: panelCount }, (_, panelIndex) => {
        const key = `${tabIndex}:${panelIndex}`
        return (state: OverviewEditState): void => {
          setEditStates((previous) => ({ ...previous, [key]: state }))
        }
      }),
    [tabIndex, panelCount],
  )
  const edits = Object.entries(editStates)
    .filter(([key]) => key.startsWith(`${tabIndex}:`))
    .map(([, state]) => state)
  return {
    editReporters,
    isDirty: edits.some((state) => state.isDirty),
    saving: edits.some((state) => state.saving),
    save: () => edits.forEach((state) => state.save()),
    revert: () => edits.forEach((state) => state.revert()),
  }
}

/** What a unit of this schema is shown as, tab by tab, as the schema lays it
 * out. A layout given here is used where it has tabs, as the verification
 * layout is; otherwise the review layout of the unit. A model that says
 * nothing gets a tab per layout it defined, so an application gains the view
 * without having to describe it first. */
export function tabsFor(
  rootSchema: RootSchema,
  schemaUid: string | undefined,
  layout: ReviewLayout | null = null,
): ReviewTabLayout[] {
  const declared = rootSchema.reviewUnit
  if (declared !== null && declared.schemaUid === schemaUid) {
    if (layout !== null && layout.tabs.length > 0) {
      return layout.tabs
    }
    if (declared.layout.tabs.length > 0) {
      return declared.layout.tabs
    }
  }
  return [
    ...rootSchema.overviewLayouts
      .filter((overview) => overview.schemaUid === schemaUid)
      .map((overview) => ({
        displayName: null,
        panels: [{ kind: 'overview' as const, layout: overview, width: null }],
      })),
    ...rootSchema.hierarchyLayouts
      .filter((hierarchy) => hierarchy.schemaUid === schemaUid)
      .map((hierarchy) => ({
        displayName: null,
        panels: [{ kind: 'hierarchy' as const, layout: hierarchy, width: null }],
      })),
  ]
}

/** What to call a tab: what it was named, or what its first panel shows. */
export function tabLabel(tab: ReviewTabLayout): string {
  if (tab.displayName !== null) {
    return tab.displayName
  }
  const panel = tab.panels[0]
  if (panel === undefined || panel.kind === 'images') {
    return 'Images'
  }
  if (panel.kind === 'non_valid_items') {
    return 'Not valid'
  }
  if (panel.kind === 'review_issues') {
    return 'Raised'
  }
  if (panel.kind === 'export_preview') {
    return 'Export'
  }
  return panel.layout.displayName
}
