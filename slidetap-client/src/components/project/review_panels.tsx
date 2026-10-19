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

import { Box, Stack, Typography } from '@mui/material'
import { type ReactElement } from 'react'
import HierarchyView from 'src/components/hierarchy/hierarchy_view'
import ImagesForItem from 'src/components/image/images_for_item_page'
import ExportNotices from 'src/components/item/export_notice'
import ExportPreview from 'src/components/item/export_preview'
import OverviewView from 'src/components/overview/overview_view'
import type { OverviewEditState } from 'src/components/overview/overview_view'
import NonValidItems from 'src/components/project/non_valid_items'
import ReviewIssues from 'src/components/project/review_issues'
import type {
  AnyReviewPanelLayout,
  ReviewTabLayout,
} from 'src/models/schema/review_layout'

/** How much of the tab a panel asked for, out of twelve. */
function panelWidth(panel: AnyReviewPanelLayout): number | undefined {
  if (panel.width === null) {
    return undefined
  }
  return panel.width.lg ?? panel.width.md ?? panel.width.xs
}

interface ReviewPanelsProps {
  projectUid: string
  batchUid?: string
  /** The unit shown. */
  itemUid: string
  tab: ReviewTabLayout | undefined
  /** What to call the kind of unit where nothing is laid out for it. */
  displayName: string
  /** The item open beside the panels, and how to open one there. */
  openedItemUid: string
  onOpenItem: (itemUid: string, siblingUids: string[]) => void
  /** Where an editable panel reports what it holds unsaved, by its index in
   * the tab. Left out, the overviews are read only. */
  editReporters?: Array<(state: OverviewEditState) => void>
}

/** The panels of one tab, side by side, each as wide as it asked to be. */
export default function ReviewPanels({
  projectUid,
  batchUid,
  itemUid,
  tab,
  displayName,
  openedItemUid,
  onOpenItem,
  editReporters,
}: ReviewPanelsProps): ReactElement {
  if (tab === undefined || tab.panels.length === 0) {
    return <Typography sx={{ p: 2 }}>Nothing is laid out for {displayName}.</Typography>
  }
  return (
    <>
      {tab.panels.map((panel, panelIndex) => (
        <Box
          key={panelIndex}
          sx={{
            // What it asked for out of twelve, or an equal share of what the
            // ones that asked have left.
            ...(panelWidth(panel) === undefined
              ? { flex: '1 1 0' }
              : {
                  width: `${(panelWidth(panel) ?? 0) * (100 / 12)}%`,
                  flexShrink: 0,
                }),
            minWidth: 0,
            height: '100%',
            minHeight: 0,
            overflowY:
              panel.kind === 'overview' || panel.kind === 'export_preview'
                ? 'auto'
                : undefined,
          }}
        >
          {panel.kind === 'review_issues' ? (
            <ReviewIssues
              key={`${itemUid}-issues-${panelIndex}`}
              reviewUnitUid={itemUid}
              openedItemUid={openedItemUid}
              onOpenItem={onOpenItem}
            />
          ) : panel.kind === 'non_valid_items' ? (
            <NonValidItems
              key={`${itemUid}-non-valid-${panelIndex}`}
              itemUid={itemUid}
              openedItemUid={openedItemUid}
              onOpenItem={onOpenItem}
            />
          ) : panel.kind === 'export_preview' ? (
            <Stack key={`${itemUid}-preview-${panelIndex}`} spacing={1}>
              <ExportNotices itemUid={itemUid} />
              <ExportPreview itemUid={itemUid} />
            </Stack>
          ) : panel.kind === 'images' ? (
            <ImagesForItem
              key={`${itemUid}-images-${panelIndex}`}
              itemUid={itemUid}
              layout={panel.layout}
            />
          ) : panel.kind === 'hierarchy' ? (
            <HierarchyView
              key={`${itemUid}-${panel.layout.uid}`}
              projectUid={projectUid}
              itemUid={itemUid}
              layout={panel.layout}
              batchUid={batchUid}
            />
          ) : (
            <OverviewView
              key={`${itemUid}-${panel.layout.uid}`}
              itemUid={itemUid}
              batchUid={batchUid}
              overviewLayout={panel.layout}
              hideHeader
              openedItemUid={openedItemUid}
              onOpenItem={onOpenItem}
              onEditStateChange={editReporters?.[panelIndex]}
            />
          )}
        </Box>
      ))}
    </>
  )
}
