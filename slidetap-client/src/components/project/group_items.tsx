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
import { Close } from '@mui/icons-material'
import { TabContext, TabList, TabPanel } from '@mui/lab'
import { Box, IconButton, Paper, Stack, Tab, Typography } from '@mui/material'
import type {
  ColumnFiltersState,
  PaginationState,
  SortingState,
} from '@tanstack/react-table'
import React, { type ReactElement } from 'react'
import { useNavigate } from 'react-router-dom'
import { ItemTable } from 'src/components/table/item_table'
import { useSchemaContext } from 'src/contexts/schema/schema_context'
import { Action } from 'src/models/action'
import type { Batch } from 'src/models/batch'
import type { Item } from 'src/models/item'
import type { Project } from 'src/models/project'
import { isReviewUnit } from 'src/models/schema/root_schema'
import type { ItemSchema } from 'src/models/schema/item_schema'
import { withSelectedBatch } from './selected_batch'

/** A set of items to list, by the schema they are of. */
export interface GroupItemsTab {
  schemaUid: string
  uids: string[]
}

interface GroupItemsProps {
  project: Project
  batch?: Batch
  /** What the items are, as the heading says it. */
  title: string
  /** Lines under the heading, such as what the items of a group share. */
  details: string[]
  /** The items, a tab per schema: the grouped items, and the review units they
   * are answered for in. */
  tabs: GroupItemsTab[]
  /** The schema of the tab open, kept by the caller so that the next group
   * opened shows the same kind of item. The first tab where not given, or
   * where this group has no tab of it. */
  tab?: string
  onTabChange?: (schemaUid: string) => void
  /** Buttons beside the heading, for what can be done with the whole set. */
  actions?: React.ReactNode
  onClose: () => void
}

/**
 * The items of a group as curate lists them: a table per kind of item, with
 * their attributes, validity and the ways into each, limited to the group.
 *
 * The grouped items first, then the units they are reviewed in, as those are
 * where something wrong with a group is put right.
 */
export default function GroupItems({
  project,
  batch,
  title,
  details,
  tabs,
  tab,
  onTabChange,
  actions,
  onClose,
}: GroupItemsProps): ReactElement {
  const rootSchema = useSchemaContext()
  const navigate = useNavigate()
  const shown = tabs
    .map((tab) => ({
      ...tab,
      schema: (rootSchema.samples[tab.schemaUid] ??
        rootSchema.images[tab.schemaUid] ??
        rootSchema.observations[tab.schemaUid] ??
        rootSchema.annotations[tab.schemaUid]) as ItemSchema | undefined,
    }))
    .filter(
      (tab): tab is GroupItemsTab & { schema: ItemSchema } =>
        tab.schema !== undefined && tab.uids.length > 0,
    )
  const [ownTab, setOwnTab] = React.useState<string>()
  const tabValue = tab ?? ownTab
  // Filtering and sorting shared across the tabs, as in curate: each table
  // applies the entries whose columns it has.
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>([])
  const [sorting, setSorting] = React.useState<SortingState>([])
  const [pagination, setPagination] = React.useState<PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  })
  const batchScope = batch !== undefined ? `?batchUid=${batch.uid}` : ''
  const itemPage = (item: Item | string): string =>
    `/project/${project.uid}/item/${typeof item === 'string' ? item : item.uid}${batchScope}`
  const activeTab =
    tabValue !== undefined &&
    shown.some((candidate) => candidate.schemaUid === tabValue)
      ? tabValue
      : (shown[0]?.schemaUid ?? '')

  return (
    <Paper variant="outlined" sx={{ p: 1 }}>
      <Stack direction="row" sx={{ alignItems: 'flex-start' }}>
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="subtitle1">{title}</Typography>
          {details.map((line) => (
            <Typography key={line} variant="body2" color="text.secondary">
              {line}
            </Typography>
          ))}
        </Box>
        {actions}
        <IconButton aria-label="Close" onClick={onClose}>
          <Close />
        </IconButton>
      </Stack>
      {shown.length === 0 ? (
        <Typography sx={{ p: 2 }}>No items to list.</Typography>
      ) : (
        <TabContext value={activeTab}>
          <TabList
            onChange={(_, value: string) => {
              setOwnTab(value)
              onTabChange?.(value)
              setPagination((previous) => ({ ...previous, pageIndex: 0 }))
            }}
          >
            {shown.map((tab) => (
              <Tab
                key={tab.schemaUid}
                value={tab.schemaUid}
                label={`${tab.schema.displayName} (${tab.uids.length})`}
              />
            ))}
          </TabList>
          {shown.map((tab) => (
            <TabPanel key={tab.schemaUid} value={tab.schemaUid} sx={{ p: 0 }}>
              <ItemTable
                project={project}
                // Not limited to the batch: the uids say which items, and the
                // unit an item of the batch is reviewed in can be of another,
                // as a shared item moves batch on a new search.
                schema={tab.schema}
                uids={tab.uids}
                compact
                rowsSelectable={false}
                actions={[
                  {
                    action: Action.WINDOW,
                    href: itemPage,
                  },
                  ...(isReviewUnit(rootSchema, tab.schemaUid)
                    ? [
                        {
                          // Into review, stopped on this unit, which is where
                          // a diagnose that makes a group too small is changed.
                          action: Action.OPEN_REVIEW,
                          onAction: (item: Item): void => {
                            navigate(
                              withSelectedBatch(
                                `/project/${project.uid}/${batch !== undefined ? 'review_batch' : 'review_dataset'}?openItem=${item.uid}`,
                                batch?.uid,
                              ),
                            )
                          },
                        },
                      ]
                    : []),
                  {
                    action: Action.IMAGES,
                    href: (item: Item): string =>
                      `/project/${project.uid}/images_for_item/${item.uid}${batchScope}`,
                  },
                  ...rootSchema.overviewLayouts
                    .filter((layout) => layout.schemaUid === tab.schemaUid)
                    .map((layout) => ({
                      action: Action.OVERVIEW,
                      href: (item: Item): string =>
                        `/project/${project.uid}/item/${item.uid}/overview/${layout.uid}${batchScope}`,
                    })),
                  ...rootSchema.hierarchyLayouts
                    .filter((layout) => layout.schemaUid === tab.schemaUid)
                    .map((layout) => ({
                      action: Action.HIERARCHY,
                      href: (item: Item): string =>
                        `/project/${project.uid}/item/${item.uid}/hierarchy/${layout.uid}${batchScope}`,
                    })),
                ]}
                onRowView={(itemUid) => navigate(itemPage(itemUid))}
                columnFilters={columnFilters}
                sorting={sorting}
                onColumnFiltersChange={(filters) => setColumnFilters(filters)}
                onSortingChange={(next) => setSorting(next)}
                pagination={pagination}
                onPaginationChange={setPagination}
                refresh={false}
              />
            </TabPanel>
          ))}
        </TabContext>
      )}
    </Paper>
  )
}
