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

import { Tab } from '@mui/material'
import React, { useEffect, useRef, useState, type ReactElement } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'
import type { Project } from 'src/models/project'

import type {
  MRT_ColumnFiltersState,
  MRT_PaginationState,
  MRT_SortingState,
} from 'material-react-table'
import { TabContext, TabList, TabPanel } from '@mui/lab'
import DisplayItemDetails from 'src/components/item/item_details'
import SplitPanel from 'src/components/split_panel'
import { ItemTable } from 'src/components/table/item_table'
import { hasFilterValue } from 'src/components/table/get_table_items'
import { useError } from 'src/contexts/error/error_context'
import { isReviewUnit, isUnderReviewUnit } from 'src/models/schema/root_schema'
import { useSchemaContext } from 'src/contexts/schema/schema_context'
import { Action, ItemDetailAction } from 'src/models/action'
import { ReviewStatus } from 'src/models/review_status'
import { Batch } from 'src/models/batch'
import { BatchStatus } from 'src/models/batch_status'
import { Item } from 'src/models/item'
import { ItemSelect } from 'src/models/item_select'
import { ItemSchema } from 'src/models/schema/item_schema'
import type { TableRequest } from 'src/models/table_item'
import itemApi from 'src/services/api/item_api'
import { queryKeys } from 'src/services/query_keys'
import { usePseudonym } from 'src/contexts/pseudonym/pseudonym_context'
import { getDisplayIdentifier } from 'src/models/pseudonym'
import ItemSelectPopover from '../item/item_select_popover'
import ReviewFlagPopover from '../item/review_flag_popover'

interface CurateProps {
  project: Project
  batch?: Batch
  itemSchemas: ItemSchema[]
}

/** How the table is being looked through: what is filtered, what it is sorted
 * by, and which page of it is shown. */
interface TableState {
  columnFilters: MRT_ColumnFiltersState
  sorting: MRT_SortingState
  pagination: MRT_PaginationState
}

const EMPTY_TABLE_STATE: TableState = {
  columnFilters: [],
  sorting: [],
  pagination: { pageIndex: 0, pageSize: 10 },
}

/** Read back what `writeTableState` put in the address, falling back to a
 * fresh table for anything it cannot make sense of. */
function readTableState(written: string | null): TableState {
  if (written === null) {
    return EMPTY_TABLE_STATE
  }
  try {
    return { ...EMPTY_TABLE_STATE, ...(JSON.parse(written) as Partial<TableState>) }
  } catch {
    return EMPTY_TABLE_STATE
  }
}

function writeTableState(state: TableState): string {
  return JSON.stringify(state)
}

export default function Curate({
  project,
  batch,
  itemSchemas,
}: CurateProps): ReactElement {
  const { showError } = useError()
  const queryClient = useQueryClient()
  const rootSchema = useSchemaContext()
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  // The kind of item being worked on is in the address, so that coming back to
  // curate comes back to the same tab.
  const openedTab =
    itemSchemas.find((schema) => schema.uid === searchParams.get('tab'))?.uid ??
    itemSchemas[0].uid
  const { pseudonymMode } = usePseudonym()
  const [tabValue, setTabValue] = useState(openedTab)
  // What the delete/restore confirmation is about, for the popover to name.
  const [itemSelectSubject, setItemSelectSubject] = useState<string>()
  const [openedTabs, setOpenedTabs] = useState<Set<string>>(() => new Set([openedTab]))
  const [itemDetailsOpen, setItemDetailsOpen] = React.useState(false)
  const [itemDetailUid, setItemDetailUid] = React.useState<string>('')
  // Curating is editing: opening an item to look at it and then having to press
  // Edit before changing anything is a step with nothing behind it. VIEW is kept
  // for a read-only dataset, which is a different job from this one.
  const [itemDetailAction, setItemDetailAction] = React.useState<ItemDetailAction>(
    ItemDetailAction.EDIT,
  )

  useEffect(() => {
    const openItem = searchParams.get('openItem')
    if (openItem) {
      setItemDetailUid(openItem)
      setItemDetailAction(ItemDetailAction.EDIT)
      setItemDetailsOpen(true)
      const next = new URLSearchParams(searchParams)
      next.delete('openItem')
      setSearchParams(next, { replace: true })
    }
  }, [searchParams, setSearchParams])
  const [privateOpen, setPrivateOpen] = useState(false)
  const [previewOpen, setPreviewOpen] = useState(false)
  const [itemSelectAnchorEl, setItemSelectAnchorEl] = useState<HTMLElement | null>(null)
  const [openedItemSelectUids, setOpenedItemSelectUids] = useState<string[]>([])
  const [openedItemSelect, setOpenedItemSelect] = useState<ItemSelect | null>(null)
  const [currentItemUids, setCurrentItemUids] = useState<string[]>([])
  const [flagAnchor, setFlagAnchor] = useState<{ top: number; left: number } | null>(
    null,
  )
  const [flagUids, setFlagUids] = useState<string[]>([])
  // Filtering, sorting and the page live here rather than in each tab's table,
  // so that filtering on an identifier or on validity survives a switch to
  // another item type. Entries for columns the new tab does not have are kept,
  // not dropped, and apply again on the way back.
  //
  // Read from the address, and written back to it below: leaving for an item
  // view unmounts this, and coming back through the bar follows a link to the
  // address it was left at.
  const openedTable = readTableState(searchParams.get('table'))
  const [columnFilters, setColumnFilters] = useState<MRT_ColumnFiltersState>(
    openedTable.columnFilters,
  )
  const [sorting, setSorting] = useState<MRT_SortingState>(openedTable.sorting)
  const [pagination, setPagination] = useState<MRT_PaginationState>(
    openedTable.pagination,
  )
  useEffect(() => {
    const next = new URLSearchParams(searchParams)
    const written = writeTableState({ columnFilters, sorting, pagination })
    if (next.get('table') === written) {
      return
    }
    next.set('table', written)
    // Replaced rather than pushed: sorting a column is not a step to go back
    // through.
    setSearchParams(next, { replace: true })
  }, [columnFilters, sorting, pagination, searchParams, setSearchParams])

  const mergeOwn = <T extends { id: string }>(
    previous: T[],
    own: T[],
    ownColumnIds: Set<string>,
  ): T[] => [...previous.filter((entry) => !ownColumnIds.has(entry.id)), ...own]
  // Each tab's ItemTable owns its own sort/filter/pagination state and posts
  // the latest TableRequest back here so the OVERVIEW row action can pass
  // that exact snapshot to the new overview window. Stored per-schema since
  // each tab uses an independent ItemTable instance.
  const tableRequestsRef = useRef<Record<string, TableRequest>>({})

  const handleSelectItemClose = () => {
    setItemSelectAnchorEl(null)
    setOpenedItemSelect(null)
    setOpenedItemSelectUids([])
  }

  const handleItemUidView = (itemUid: string): void => {
    setItemDetailUid(itemUid)
    setItemDetailAction(ItemDetailAction.EDIT)
    setItemDetailsOpen(true)
  }

  const handleItemEdit = (item: Item): void => {
    setItemDetailUid(item.uid)
    setItemDetailAction(ItemDetailAction.EDIT)
    setItemDetailsOpen(true)
  }

  const handleItemDeleteOrRestore = (item: Item, element: HTMLElement): void => {
    setItemSelectSubject(getDisplayIdentifier(item, pseudonymMode))
    setOpenedItemSelect({
      select: !item.selected,
      comment: item.comment,
      tags: item.tags,
      additiveTags: false,
    })
    setOpenedItemSelectUids([item.uid])
    setItemSelectAnchorEl(element)
  }

  const handleStateChange = (
    itemUids: string[],
    state: boolean,
    element: HTMLElement,
  ): void => {
    // Named by how many of what, since the button acts on the selection rather
    // than on a row anything points at.
    const schema = itemSchemas.find((candidate) => candidate.uid === tabValue)
    setItemSelectSubject(
      `${itemUids.length} ${schema?.displayName ?? 'item'}${
        itemUids.length === 1 ? '' : 's'
      }`,
    )
    setOpenedItemSelect({
      select: state,
      comment: null,
      tags: [],
      additiveTags: true,
    })
    setOpenedItemSelectUids(itemUids)
    setItemSelectAnchorEl(element)
  }

  const openFlagForReview = (itemUids: string[], element: HTMLElement): void => {
    // The position is taken now, while the button is still on screen: the one
    // in the identifier panel is gone by the time the popover renders.
    const rect = element.getBoundingClientRect()
    setFlagUids(itemUids)
    setFlagAnchor({ top: rect.bottom, left: rect.left + rect.width / 2 })
  }

  const handleFlagClose = (): void => {
    setFlagAnchor(null)
    setFlagUids([])
  }

  const setReviewStatus = (
    itemUids: string[],
    status: ReviewStatus,
    reason?: string,
  ): void => {
    void Promise.all(
      itemUids.map(async (uid) => await itemApi.setReviewStatus(uid, status, reason)),
    )
      .catch((error) => {
        showError('Failed to set review status', error)
      })
      .finally(() => {
        void queryClient.invalidateQueries({ queryKey: queryKeys.item.all })
      })
  }

  // Raised on the item that looked wrong, whatever kind it is, and answered
  // on the review unit above it: a block is usually only decidable with the
  // whole case in front of you.
  const flagForReview = (itemUids: string[], reason: string | null): void => {
    void Promise.all(
      itemUids.map(async (uid) => await itemApi.raiseReviewIssue(uid, reason ?? '')),
    )
      .then(() => {
        void queryClient.invalidateQueries({ queryKey: queryKeys.item.all })
      })
      .catch((error) => {
        showError('Failed to raise review issue', error)
      })
  }

  const handleRowsRemap = (itemUids: string[]): void => {
    void Promise.all(itemUids.map((uid) => itemApi.remap(uid)))
      .catch((error) => {
        showError('Failed to remap items', error)
      })
      .finally(() => {
        // Remapping rewrites attribute values and revalidates, so the table is
        // stale until it refetches.
        void queryClient.invalidateQueries({ queryKey: queryKeys.item.all })
      })
  }

  return (
    <React.Fragment>
      <SplitPanel
        panel={
          itemDetailsOpen &&
          itemDetailUid !== '' && (
            <DisplayItemDetails
              projectUid={project.uid}
              itemUid={itemDetailUid}
              action={itemDetailAction}
              privateOpen={privateOpen}
              previewOpen={previewOpen}
              setOpen={setItemDetailsOpen}
              setItemUid={setItemDetailUid}
              setItemAction={setItemDetailAction}
              setPrivateOpen={setPrivateOpen}
              setPreviewOpen={setPreviewOpen}
              windowed={false}
              itemUids={currentItemUids}
            />
          )
        }
      >
        <TabContext value={tabValue}>
          <TabList
            onChange={(_, newValue) => {
              setTabValue(newValue)
              setOpenedTabs((previous) => new Set(previous).add(newValue as string))
              // Back to the first page, keeping how many rows are shown: the
              // page is a position in one list, and eight blocks have no page
              // four to land on. How long a page is is a preference, and
              // belongs to the reader rather than to the list.
              setPagination((previous) => ({ ...previous, pageIndex: 0 }))
              // Written to the address so that leaving for an item and coming
              // back through the bar lands on the same kind of item. Replaced
              // rather than pushed: switching tabs is not a step to go back
              // through.
              const next = new URLSearchParams(searchParams)
              next.set('tab', newValue as string)
              setSearchParams(next, { replace: true })
            }}
          >
            {itemSchemas.map((schema) => (
              <Tab key={schema.uid} value={schema.uid} label={schema.displayName} />
            ))}
          </TabList>
          {itemSchemas.map((schema) => (
            // Kept mounted once opened: a tab that unmounts refetches and
            // relays out on every switch. Not mounted before its first visit,
            // so opening the page still loads one table rather than all of them.
            <TabPanel
              key={schema.uid}
              value={schema.uid}
              keepMounted={openedTabs.has(schema.uid)}
              style={{ padding: 0 }}
            >
              <ItemTable
                project={project}
                batch={batch}
                schema={schema}
                rowsSelectable={true}
                actions={[
                  // No view action: the identifier chip is the link that opens
                  // the item.
                  { action: Action.EDIT, onAction: handleItemEdit },
                  // Left out rather than disabled where nothing above the
                  // schema is reviewed: an action that can never apply to any
                  // row of the tab is not a state to show, and a dead flag on
                  // every row reads as something that ought to work.
                  //
                  // Raising is offered wherever there is a unit to answer for
                  // the row, which is most of the hierarchy — a block that
                  // looks wrong is raised on the block.
                  ...(isUnderReviewUnit(rootSchema, schema.uid)
                    ? [
                        {
                          action: Action.REVIEW,
                          onAction: (item: Item, element: HTMLElement): void =>
                            openFlagForReview([item.uid], element),
                          pin: true,
                        },
                      ]
                    : []),
                  // Working through the queue and signing off happen on the
                  // unit itself, so these stay on the rows that are one.
                  ...(isReviewUnit(rootSchema, schema.uid)
                    ? [
                        // Into the view that works through these one at a time,
                        // stopped on this one. Navigated rather than opened in a
                        // window: reviewing is where the work moves to, not
                        // something to glance at beside the table.
                        {
                          action: Action.OPEN_REVIEW,
                          onAction: (item: Item): void => {
                            navigate(
                              `/project/${project.uid}/review?openItem=${item.uid}`,
                            )
                          },
                        },
                        {
                          action: Action.MARK_REVIEWED,
                          onAction: (item: Item): void =>
                            setReviewStatus([item.uid], ReviewStatus.Reviewed),
                          enabled: (item: Item): boolean =>
                            item.reviewStatus === ReviewStatus.Flagged,
                          hideWhenDisabled: true,
                        },
                      ]
                    : []),
                  {
                    action: Action.DELETE,
                    onAction: handleItemDeleteOrRestore,
                  },
                  {
                    action: Action.RESTORE,
                    onAction: handleItemDeleteOrRestore,
                  },
                  // The views of an item are links rather than buttons that
                  // open a window: a click goes there, and the browser keeps
                  // its own middle-click, ctrl-click and "open in new window"
                  // for anyone who wants it beside the table instead.
                  {
                    action: Action.WINDOW,
                    href: (item: Item): string =>
                      `/project/${project.uid}/item/${item.uid}`,
                  },
                  {
                    action: Action.IMAGES,
                    href: (item: Item): string =>
                      `/project/${project.uid}/images_for_item/${item.uid}`,
                    enabled: (): boolean => {
                      return (
                        batch != undefined &&
                        batch?.status >= BatchStatus.IMAGE_PRE_PROCESSING
                      )
                    },
                  },
                  // Every layout the schema lists is a way into an item; one
                  // written to be read beside another is not listed, but
                  // nested in whatever composes it.
                  ...rootSchema.overviewLayouts
                    .filter((layout) => layout.schemaUid === schema.uid)
                    .map((layout) => ({
                      action: Action.OVERVIEW,
                      href: (item: Item): string => {
                        const params = new URLSearchParams()
                        if (batch) params.set('batchUid', batch.uid)
                        const snapshot = tableRequestsRef.current[schema.uid]
                        if (snapshot) {
                          params.set('tableRequest', JSON.stringify(snapshot))
                        }
                        const qs = params.toString()
                        return `/project/${project.uid}/item/${item.uid}/overview/${layout.uid}${qs ? `?${qs}` : ''}`
                      },
                    })),
                  // What hangs under the item, on the same terms.
                  ...rootSchema.hierarchyLayouts
                    .filter((layout) => layout.schemaUid === schema.uid)
                    .map((layout) => ({
                      action: Action.HIERARCHY,
                      href: (item: Item): string =>
                        `/project/${project.uid}/item/${item.uid}/hierarchy/${layout.uid}`,
                    })),
                ]}
                onRowsStateChange={handleStateChange}
                onRowsRemap={handleRowsRemap}
                onRowsFlagForReview={
                  isUnderReviewUnit(rootSchema, schema.uid)
                    ? openFlagForReview
                    : undefined
                }
                onRowsMarkReviewed={
                  isReviewUnit(rootSchema, schema.uid)
                    ? (uids) => setReviewStatus(uids, ReviewStatus.Reviewed)
                    : undefined
                }
                onRowView={handleItemUidView}
                onTableRequestChange={(request) => {
                  tableRequestsRef.current[schema.uid] = request
                }}
                onNew={
                  batch !== undefined
                    ? async (): Promise<void> => {
                        const newItem = await itemApi.create(schema.uid, batch.uid)
                        setItemDetailUid(newItem.uid)
                        setItemDetailAction(ItemDetailAction.EDIT)
                        setItemDetailsOpen(true)
                      }
                    : undefined
                }
                columnFilters={columnFilters}
                sorting={sorting}
                // One page across the tabs: they are looked through one at a
                // time, and a page kept per tab would need the row counts of
                // tabs nobody has opened.
                pagination={pagination}
                onPaginationChange={setPagination}
                onColumnFiltersChange={(filters, ownColumnIds) => {
                  // Clearing a filter input leaves an entry with an empty
                  // value behind. Kept, it would sit in this state forever and
                  // the column would count as filtered although it is not.
                  setColumnFilters((previous) =>
                    mergeOwn(
                      previous,
                      filters.filter((filter) => hasFilterValue(filter.value)),
                      ownColumnIds,
                    ),
                  )
                }}
                onSortingChange={(newSorting, ownColumnIds) => {
                  setSorting((previous) => mergeOwn(previous, newSorting, ownColumnIds))
                }}
                onItemUidsChange={setCurrentItemUids}
                refresh={batch?.status === BatchStatus.METADATA_SEARCHING}
              />
            </TabPanel>
          ))}
        </TabContext>
      </SplitPanel>
      {flagAnchor !== null && (
        <ReviewFlagPopover
          anchorPosition={flagAnchor}
          count={flagUids.length}
          onClose={handleFlagClose}
          onConfirm={(reason) => {
            flagForReview(flagUids, reason)
            handleFlagClose()
          }}
        />
      )}
      {openedItemSelect && (
        <ItemSelectPopover
          anchorEl={itemSelectAnchorEl}
          select={openedItemSelect.select}
          subject={itemSelectSubject}
          comment={openedItemSelect.comment}
          tags={openedItemSelect.tags}
          additiveTags={openedItemSelect.additiveTags}
          onClose={handleSelectItemClose}
          onConfirm={(value) => {
            void Promise.all(
              openedItemSelectUids.map((uid) => itemApi.select(uid, value)),
            )
              .catch((error) => {
                showError('Failed to select item', error)
              })
              .finally(() => {
                // Deleted items drop out of the table and restored ones
                // reappear, but only once the tables refetch. Deleting cascades
                // to children, images and observations, so every item type can
                // be affected, not just this row's.
                void queryClient.invalidateQueries({ queryKey: queryKeys.item.all })
              })
            handleSelectItemClose()
          }}
        />
      )}
    </React.Fragment>
  )
}
