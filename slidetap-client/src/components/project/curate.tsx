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

import type { MRT_ColumnFiltersState, MRT_SortingState } from 'material-react-table'
import { TabContext, TabList, TabPanel } from '@mui/lab'
import DisplayItemDetails from 'src/components/item/item_details'
import SplitPanel from 'src/components/split_panel'
import { ItemTable } from 'src/components/table/item_table'
import { hasFilterValue } from 'src/components/table/get_table_items'
import { useError } from 'src/contexts/error/error_context'
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
import ItemSelectPopover from '../item/item_select_popover'
import ReviewFlagPopover from '../item/review_flag_popover'

interface CurateProps {
  project: Project
  batch?: Batch
  itemSchemas: ItemSchema[]
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
  const [tabValue, setTabValue] = useState(itemSchemas[0].uid)
  const [openedTabs, setOpenedTabs] = useState<Set<string>>(
    () => new Set([itemSchemas[0].uid]),
  )
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
  // Filtering and sorting live here rather than in each tab's table, so that
  // filtering on an identifier or on validity survives a switch to another item
  // type. Entries for columns the new tab does not have are kept, not dropped,
  // and apply again on the way back.
  const [columnFilters, setColumnFilters] = useState<MRT_ColumnFiltersState>([])
  const [sorting, setSorting] = useState<MRT_SortingState>([])

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

  const flagForReview = (itemUids: string[], reason: string | null): void => {
    setReviewStatus(itemUids, ReviewStatus.Flagged, reason ?? undefined)
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
                  // Left out rather than disabled where the schema is not what
                  // a reviewer works through: an action that can never apply to
                  // any row of the tab is not a state to show, and a dead flag
                  // on every row reads as something that ought to work.
                  ...(schema.reviewUnit
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
                        // One action per state, and the colour of its flag is
                        // the state rather than what the click does: the flag
                        // is a request to look, so the only way out of it is
                        // to say someone has.
                        {
                          action: Action.REVIEW,
                          onAction: (item: Item, element: HTMLElement): void =>
                            openFlagForReview([item.uid], element),
                          pin: true,
                          enabled: (item: Item): boolean =>
                            item.reviewStatus !== ReviewStatus.Flagged,
                          hideWhenDisabled: true,
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
                  {
                    action: Action.IMAGES,
                    onAction: (item: Item): void => {
                      window.open(
                        `/project/${project.uid}/images_for_item/${item.uid}`,
                        '_blank',
                        'noopener,noreferrer,width=1024,height=1024,menubar=no,toolbar=no,location=no,status=no,scrollbars=yes,resizable=yes',
                      )
                    },
                    enabled: (): boolean => {
                      return (
                        batch != undefined &&
                        batch?.status >= BatchStatus.IMAGE_PRE_PROCESSING
                      )
                    },
                  },
                  {
                    action: Action.WINDOW,
                    onAction: (item: Item): void => {
                      window.open(
                        `/project/${project.uid}/item/${item.uid}`,
                        '_blank',
                        'noopener,noreferrer,width=600,height=800,menubar=no,toolbar=no,location=no,status=no,scrollbars=yes,resizable=yes',
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
                      onAction: (item: Item): void => {
                        const params = new URLSearchParams()
                        if (batch) params.set('batchUid', batch.uid)
                        const snapshot = tableRequestsRef.current[schema.uid]
                        if (snapshot) {
                          params.set('tableRequest', JSON.stringify(snapshot))
                        }
                        const qs = params.toString()
                        window.open(
                          `/project/${project.uid}/item/${item.uid}/overview/${layout.uid}${qs ? `?${qs}` : ''}`,
                          '_blank',
                          'noopener,noreferrer,width=1400,height=900,menubar=no,toolbar=no,location=no,status=no,scrollbars=yes,resizable=yes',
                        )
                      },
                    })),
                  // What hangs under the item, on the same terms: a window of
                  // its own, for reading the tree without the review queue.
                  ...rootSchema.hierarchyLayouts
                    .filter((layout) => layout.schemaUid === schema.uid)
                    .map((layout) => ({
                      action: Action.HIERARCHY,
                      onAction: (item: Item): void => {
                        window.open(
                          `/project/${project.uid}/item/${item.uid}/hierarchy/${layout.uid}`,
                          '_blank',
                          'noopener,noreferrer,width=900,height=700,menubar=no,toolbar=no,location=no,status=no,scrollbars=yes,resizable=yes',
                        )
                      },
                    })),
                ]}
                onRowsStateChange={handleStateChange}
                onRowsRemap={handleRowsRemap}
                onRowsFlagForReview={schema.reviewUnit ? openFlagForReview : undefined}
                onRowsMarkReviewed={
                  schema.reviewUnit
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
