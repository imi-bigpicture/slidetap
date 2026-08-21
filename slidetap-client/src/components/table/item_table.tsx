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

import {
  Add,
  AutoFixHigh,
  Flag,
  OutlinedFlag,
  Delete,
  Done,
  PriorityHigh,
  Recycling,
  RestoreFromTrash,
  WarningTwoTone,
} from '@mui/icons-material'
import {
  Box,
  Chip,
  CircularProgress,
  Divider,
  IconButton,
  MenuItem,
  Stack,
  Tooltip,
  lighten,
} from '@mui/material'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import {
  MRT_Cell,
  MRT_ColumnDef,
  MRT_GlobalFilterTextField,
  MRT_ToggleFiltersButton,
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnFiltersState,
  type MRT_PaginationState,
  type MRT_SortingState,
  type MRT_Updater,
} from 'material-react-table'
import React, { useEffect, useMemo, useState } from 'react'
import { Action, ActionStrings, ItemDetailAction } from 'src/models/action'
import { Batch } from 'src/models/batch'
import {
  isAnnotationItem,
  isAnnotationSchema,
  isImageItem,
  isImageSchema,
  isObservationItem,
  isSampleItem,
  isSampleSchema,
} from 'src/models/helpers'
import { Item } from 'src/models/item'
import { getDisplayIdentifier } from 'src/models/pseudonym'
import { Project } from 'src/models/project'
import { AttributeDisplay, isShown } from 'src/models/schema/attribute_schema'
import { allowsMultiple } from 'src/models/schema/cardinality'
import type { ItemSchema } from 'src/models/schema/item_schema'
import {
  AttributeValueField,
  RelationFilterType,
  type RelationFilterDefinition,
} from 'src/models/table_item'
import { usePseudonym } from 'src/contexts/pseudonym/pseudonym_context'
import { Tag } from 'src/models/tag'
import { TableRequest } from 'src/models/table_item'
import itemApi from 'src/services/api/item_api'
import tagApi from 'src/services/api/tag_api'
import { queryKeys } from 'src/services/query_keys'
import DisplayAttribute from '../attribute/display_attribute'
import { buildTableRequest, getItems } from './get_table_items'
import { ValueActions, type ValueAction } from './value_actions'
import ActionsIcons from './action_icons'

const ATTRIBUTE_VALUE_FIELD_LABELS: Record<AttributeValueField, string> = {
  [AttributeValueField.DISPLAY]: 'Display value',
  [AttributeValueField.MAPPABLE]: 'Mappable value',
}

interface ItemTableProps {
  project: Project
  batch?: Batch
  schema: ItemSchema
  rowsSelectable?: boolean
  actions?: {
    action: Action
    /** What the action does. Left out for one that only opens a view — see
     * `href`. */
    onAction?: (item: Item, element: HTMLElement) => void
    /** Where the action goes, for one that opens a view of the item. Rendered
     * as a link, so the browser keeps its own ways of opening it. */
    href?: (item: Item) => string
    enabled?: (item: Item) => boolean
    /** Leave the action out for items it does not apply to, rather than showing
     * it greyed. For actions whose whole meaning is the state the item is in:
     * a greyed one reads as broken rather than as not applicable. */
    hideWhenDisabled?: boolean
    /** Keep the identifier panel open after the click: this action opens a
     * popover of its own. */
    pin?: boolean
    inMenu?: boolean
  }[]
  onRowsStateChange?: (itemUids: string[], state: boolean, element: HTMLElement) => void
  onRowsRemap?: (itemUids: string[]) => void
  /** Flag every selected item for review. Reviewing is one item at a time, but
   * noticing that a batch of them needs it is not. */
  onRowsFlagForReview?: (itemUids: string[], element: HTMLElement) => void
  /** Mark every selected item reviewed. Needs no reason: the answer to why it
   * was asked for is that someone has now looked. */
  onRowsMarkReviewed?: (itemUids: string[]) => void
  onRowView: (itemUid: string) => void
  onNew?: () => void
  onItemUidsChange?: (itemUids: string[]) => void
  onTableRequestChange?: (request: TableRequest) => void
  /** Filtering and sorting are owned by the parent so they survive a switch to
   * another item type: each table applies the entries whose column it has, and
   * reports back which those were. */
  columnFilters: MRT_ColumnFiltersState
  sorting: MRT_SortingState
  onColumnFiltersChange: (
    filters: MRT_ColumnFiltersState,
    ownColumnIds: Set<string>,
  ) => void
  onSortingChange: (sorting: MRT_SortingState, ownColumnIds: Set<string>) => void
  /** Which page is shown, for a caller that keeps it across a visit somewhere
   * else. Kept here when not given. */
  pagination?: MRT_PaginationState
  onPaginationChange?: (pagination: MRT_PaginationState) => void
  refresh: boolean
}

/** The identifier column holds this width whatever it contains, so it sits in
 * the same place in every tab, and grows past it only where the identifiers are
 * genuinely longer — they are never cut off. Monospace makes the needed width
 * predictable from the character count. */
const IDENTIFIER_MIN_WIDTH = 180
const IDENTIFIER_MAX_WIDTH = 440
const IDENTIFIER_CHAR_WIDTH = 8.4
/** Chip padding, border, chevron and the cell's own padding around the text. */
const IDENTIFIER_CHROME_WIDTH = 62

/** Column id for an attribute, matched against the shared filter and sort
 * state, so keep it in step with the attribute columns built below. */
const attributeColumnId = (tag: string, isPrivate: boolean): string =>
  `${isPrivate ? 'privateAttributes' : 'attributes'}.${tag}`

export function ItemTable({
  project,
  batch,
  schema,
  rowsSelectable,
  actions,
  onRowsStateChange,
  onRowsRemap,
  onRowsFlagForReview,
  onRowsMarkReviewed,
  onRowView,
  onNew,
  onItemUidsChange,
  onTableRequestChange,
  columnFilters,
  sorting,
  onColumnFiltersChange,
  onSortingChange,
  pagination: controlledPagination,
  onPaginationChange,
  refresh,
}: ItemTableProps): React.ReactElement {
  const { pseudonymMode } = usePseudonym()
  // Held by the caller when it wants the page kept — leaving for an item view
  // and coming back should land on the page the work was on.
  const [ownPagination, setOwnPagination] = useState<MRT_PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  })
  const pagination = controlledPagination ?? ownPagination
  const setPagination = (updater: MRT_Updater<MRT_PaginationState>): void => {
    const next = updater instanceof Function ? updater(pagination) : updater
    setOwnPagination(next)
    onPaginationChange?.(next)
  }
  // Value shown, filtered and sorted on per attribute column, keyed by column id.
  const [attributeValueFields, setAttributeValueFields] = useState<
    Record<string, AttributeValueField>
  >({})
  const [displayRecycled, setDisplayRecycled] = useState(false)
  const [displayOnlyInValid, setDisplayOnlyInValid] = useState(false)
  const relationships = useMemo<Record<string, RelationFilterDefinition>>(() => {
    const relationships: Record<string, RelationFilterDefinition> = {}
    if (isSampleSchema(schema)) {
      // Only where there can be more than one: a column that reads 0 or 1 is
      // not worth a column, and filtering on its count says nothing.
      schema.children
        .filter((relation) => allowsMultiple(relation.children))
        .forEach((schema) => {
          relationships[`relation.${schema.uid}.child.${schema.childUid}`] = {
            title: schema.childTitle,
            relationSchemaUid: schema.childUid,
            relationType: RelationFilterType.CHILD,
            valueGetter: (item: Item) =>
              isSampleItem(item) ? (item.children?.[schema.childUid]?.length ?? 0) : 0,
          }
        })
      schema.parents
        .filter((relation) => allowsMultiple(relation.parents))
        .forEach((schema) => {
          relationships[`relation.${schema.uid}.parent.${schema.parentUid}`] = {
            title: schema.parentTitle,
            relationSchemaUid: schema.parentUid,
            relationType: RelationFilterType.PARENT,
            valueGetter: (item: Item) =>
              isSampleItem(item) ? (item.parents?.[schema.parentUid]?.length ?? 0) : 0,
          }
        })
      schema.images.forEach((schema) => {
        relationships[`relation.${schema.uid}.image.${schema.imageUid}`] = {
          title: schema.imageTitle,
          relationSchemaUid: schema.imageUid,
          relationType: RelationFilterType.IMAGE,
          valueGetter: (item: Item) =>
            isSampleItem(item) ? (item.images?.[schema.imageUid]?.length ?? 0) : 0,
        }
      })
      schema.observations.forEach((schema) => {
        relationships[`relation.${schema.uid}.observation.${schema.observationUid}`] = {
          title: schema.observationTitle,
          relationSchemaUid: schema.observationUid,
          relationType: RelationFilterType.OBSERVATION,
          valueGetter: (item: Item) =>
            isSampleItem(item)
              ? (item.observations?.[schema.observationUid]?.length ?? 0)
              : 0,
        }
      })
    } else if (isImageSchema(schema)) {
      // Not the orphan relation: it says where an image was parked for want of
      // anywhere better, which is not something to count, filter or sort the
      // images by. The sample holding them still shows its own count.
      schema.samples
        .filter((relation) => !relation.orphan)
        .forEach((schema) => {
          relationships[`relation.${schema.uid}.sample.${schema.sampleUid}`] = {
            title: schema.sampleTitle,
            relationSchemaUid: schema.sampleUid,
            relationType: RelationFilterType.SAMPLE,
            valueGetter: (item: Item) =>
              isImageItem(item) ? (item.samples?.[schema.sampleUid]?.length ?? 0) : 0,
          }
        })
      schema.annotations.forEach((schema) => {
        relationships[`relation.${schema.uid}.annotation.${schema.annotationUid}`] = {
          title: schema.annotationTitle,
          relationSchemaUid: schema.annotationUid,
          relationType: RelationFilterType.ANNOTATION,
          valueGetter: (item: Item) =>
            isImageItem(item)
              ? (item.annotations?.[schema.annotationUid]?.length ?? 0)
              : 0,
        }
      })
      schema.observations.forEach((schema) => {
        relationships[`relation.${schema.uid}.observation.${schema.observationUid}`] = {
          title: schema.observationTitle,
          relationSchemaUid: schema.observationUid,
          relationType: RelationFilterType.OBSERVATION,
          valueGetter: (item: Item) =>
            isImageItem(item)
              ? (item.observations?.[schema.observationUid]?.length ?? 0)
              : 0,
        }
      })
    } else if (isAnnotationSchema(schema)) {
      schema.observations.forEach((observationSchema) => {
        relationships[
          `relation.${observationSchema.uid}.observation.${observationSchema.observationUid}`
        ] = {
          title: observationSchema.observationTitle,
          relationSchemaUid: observationSchema.observationUid,
          relationType: RelationFilterType.OBSERVATION,
          valueGetter: (item: Item) =>
            isAnnotationItem(item)
              ? (item.observations?.[observationSchema.observationUid]?.length ?? 0)
              : 0,
        }
      })
    }
    return relationships
  }, [schema])

  const ownColumnIds = useMemo(
    () =>
      new Set<string>([
        'id',
        'valid',
        'tags',
        ...Object.values(schema.attributes)
          .filter((attributeSchema) => isShown(attributeSchema, AttributeDisplay.Table))
          .map((attributeSchema) => attributeColumnId(attributeSchema.tag, false)),
        ...Object.values(schema.privateAttributes)
          .filter((attributeSchema) => isShown(attributeSchema, AttributeDisplay.Table))
          .map((attributeSchema) => attributeColumnId(attributeSchema.tag, true)),
        ...Object.keys(relationships),
      ]),
    [schema, relationships],
  )

  // Entries for columns this item type does not have are left alone rather than
  // dropped: they belong to another tab and are restored on the way back.
  const ownFilters = useMemo(
    () => columnFilters.filter((filter) => ownColumnIds.has(filter.id)),
    [columnFilters, ownColumnIds],
  )
  const ownSorting = useMemo(
    () => sorting.filter((sort) => ownColumnIds.has(sort.id)),
    [sorting, ownColumnIds],
  )

  const handleColumnFiltersChange = (
    updater: MRT_Updater<MRT_ColumnFiltersState>,
  ): void => {
    onColumnFiltersChange(
      typeof updater === 'function' ? updater(ownFilters) : updater,
      ownColumnIds,
    )
  }
  const handleSortingChange = (updater: MRT_Updater<MRT_SortingState>): void => {
    onSortingChange(
      typeof updater === 'function' ? updater(ownSorting) : updater,
      ownColumnIds,
    )
  }

  const itemsQuery = useQuery({
    queryKey: queryKeys.item.table(
      schema.uid,
      project.datasetUid,
      batch?.uid,
      relationships,
      pagination.pageIndex * pagination.pageSize,
      pagination.pageSize,
      ownFilters,
      ownSorting,
      displayRecycled,
      displayOnlyInValid,
      pseudonymMode,
      attributeValueFields,
    ),
    queryFn: async () => {
      return await getItems<Item>(
        schema.uid,
        project.datasetUid,
        batch ? batch : null,
        relationships,
        pagination.pageIndex * pagination.pageSize,
        pagination.pageSize,
        ownFilters,
        ownSorting,
        attributeValueFields,
        displayRecycled,
        displayOnlyInValid ? true : undefined,
        pseudonymMode,
      )
    },
    refetchInterval: refresh ? 2000 : false,
    placeholderData: keepPreviousData,
  })
  useEffect(() => {
    if (itemsQuery.data?.items) {
      onItemUidsChange?.(itemsQuery.data.items.map((item) => item.uid))
    }
  }, [itemsQuery.data?.items, onItemUidsChange])

  useEffect(() => {
    if (!onTableRequestChange) return
    onTableRequestChange(
      buildTableRequest(
        relationships,
        pagination.pageIndex * pagination.pageSize,
        pagination.pageSize,
        ownFilters,
        ownSorting,
        attributeValueFields,
        displayRecycled,
        displayOnlyInValid ? true : undefined,
        pseudonymMode,
      ),
    )
  }, [
    onTableRequestChange,
    relationships,
    pagination.pageIndex,
    pagination.pageSize,
    ownFilters,
    ownSorting,
    attributeValueFields,
    displayRecycled,
    displayOnlyInValid,
    pseudonymMode,
  ])

  const tagsQuery = useQuery({
    queryKey: queryKeys.tag.list(),
    queryFn: async () => {
      return await tagApi.getTags()
    },
  })

  const handleRowsState = (element: HTMLElement): void => {
    if (displayRecycled === undefined) {
      return
    }
    onRowsStateChange?.(
      table.getSelectedRowModel().flatRows.map((row) => row.id),
      displayRecycled,
      element,
    )
  }

  const handleRowsRemap = (): void => {
    onRowsRemap?.(table.getSelectedRowModel().flatRows.map((row) => row.id))
  }

  const handleRowsFlagForReview = (element: HTMLElement): void => {
    onRowsFlagForReview?.(
      table.getSelectedRowModel().flatRows.map((row) => row.id),
      element,
    )
  }

  const handleRowsMarkReviewed = (): void => {
    onRowsMarkReviewed?.(table.getSelectedRowModel().flatRows.map((row) => row.id))
  }

  const handleNew = (): void => {
    onNew?.()
  }

  /** The row's actions, listed in the identifier's hover panel. Delete and
   * restore are two views of the same action, so only the one matching the
   * current recycled filter is offered. */
  const rowActions = (item: Item): ValueAction[] =>
    (actions ?? [])
      .filter((action) =>
        displayRecycled
          ? action.action !== Action.DELETE
          : action.action !== Action.RESTORE,
      )
      .filter(
        (action) =>
          action.hideWhenDisabled !== true ||
          action.enabled === undefined ||
          action.enabled(item),
      )
      .map((action) => ({
        key: `${action.action}`,
        icon: ActionsIcons[action.action],
        label: ActionStrings[action.action],
        onClick: (anchor: HTMLElement) => action.onAction?.(item, anchor),
        href: action.href?.(item),
        pin: action.pin,
        disabled: action.enabled !== undefined && !action.enabled(item),
      }))

  const identifierColumnSize = useMemo(() => {
    const longest = (itemsQuery.data?.items ?? []).reduce(
      (longest, item) =>
        Math.max(longest, getDisplayIdentifier(item, pseudonymMode).length),
      0,
    )
    return Math.min(
      IDENTIFIER_MAX_WIDTH,
      Math.max(
        IDENTIFIER_MIN_WIDTH,
        longest * IDENTIFIER_CHAR_WIDTH + IDENTIFIER_CHROME_WIDTH,
      ),
    )
  }, [itemsQuery.data?.items, pseudonymMode])

  const columns: MRT_ColumnDef<Item>[] = [
    {
      id: 'id',
      header: pseudonymMode ? 'Pseudonym' : 'Identifier',
      accessorKey: 'identifier',
      size: identifierColumnSize,
      minSize: IDENTIFIER_MIN_WIDTH,
      muiFilterTextFieldProps: {
        placeholder: pseudonymMode ? 'Pseudonym' : 'Identifier',
      },
      Cell: ({ row }) => {
        const item = row.original
        return (
          // The identifier is the way into the item and everything the row can
          // do hangs off it. Name, pseudonym and comment live in the detail
          // panel it opens, so no popover here.
          <ValueActions
            value={getDisplayIdentifier(item, pseudonymMode)}
            monospace
            onOpen={() => onRowView(item.uid)}
            copyable
            copyLabel="Copy identifier"
            actions={rowActions(item)}
          />
        )
      },
    },
    {
      id: 'valid',
      header: 'Valid',
      accessorKey: 'valid',
      filterVariant: 'select',
      filterSelectOptions: [
        { label: 'Valid', value: 'true' },
        { label: 'Invalid', value: 'false' },
      ],
      // Set by the header rather than the body: the label and the sort arrow
      // need more room than the status icon below them, with headroom so the
      // label is never on the edge of clipping.
      size: 100,
      Cell: ({ cell }) =>
        cell.getValue<boolean>() ? (
          <Done color="success" />
        ) : (
          <PriorityHigh color="warning" />
        ),
    },
    ...[
      ...Object.values(schema.attributes).map((attributeSchema) => ({
        attributeSchema,
        private: false,
      })),
      ...Object.values(schema.privateAttributes).map((attributeSchema) => ({
        attributeSchema,
        private: true,
      })),
    ]
      .filter(({ attributeSchema }) => isShown(attributeSchema, AttributeDisplay.Table))
      .map(({ attributeSchema, private: isPrivate }) => {
        const columnId = attributeColumnId(attributeSchema.tag, isPrivate)
        const valueField = attributeValueFields[columnId] ?? AttributeValueField.DISPLAY
        return {
          id: columnId,
          header: attributeSchema.displayName,
          accessorKey: `${columnId}.${
            valueField === AttributeValueField.MAPPABLE
              ? 'mappableValue'
              : 'displayValue'
          }`,
          size: 180,
          // Attributes absorb the leftover width, so the columns before them
          // keep exactly their own size in every tab.
          grow: 1,
          // What the box can be asked, said where it is asked: the syntax is
          // not guessable, and a column of codes is exactly where wanting all
          // but one of them comes up.
          muiFilterTextFieldProps: {
            title:
              'Several terms, separated by commas: a row matching any of them ' +
              'is kept. A term starting with ! excludes the rows matching it. ' +
              'Quote a term to take it as it stands.',
          },
          renderColumnActionsMenuItems: ({
            internalColumnMenuItems,
            closeMenu,
          }: {
            internalColumnMenuItems: React.ReactNode[]
            closeMenu: () => void
          }) => [
            ...internalColumnMenuItems,
            <Divider key="value-field-divider" />,
            ...Object.values(AttributeValueField).map((field) => (
              <MenuItem
                key={field}
                selected={field === valueField}
                onClick={() => {
                  setAttributeValueFields((fields) => ({
                    ...fields,
                    [columnId]: field,
                  }))
                  closeMenu()
                }}
              >
                {ATTRIBUTE_VALUE_FIELD_LABELS[field]}
              </MenuItem>
            )),
          ],

          Cell: ({ row }: { row: MRT_Cell<Item>['row'] }) => {
            const item = row.original
            const attribute = (isPrivate ? item.privateAttributes : item.attributes)[
              attributeSchema.tag
            ]
            const label =
              valueField === AttributeValueField.MAPPABLE
                ? attribute?.mappableValue
                : attribute?.displayValue
            if (attribute === undefined || !label) {
              return null
            }
            return (
              <ValueActions
                value={label}
                quiet
                content={
                  // Not displayAsRoot: the attribute keeps its own framed
                  // label, which needs a little headroom for the legend.
                  <Box sx={{ pt: 1 }}>
                    <DisplayAttribute
                      attribute={attribute}
                      schema={attributeSchema}
                      action={ItemDetailAction.VIEW}
                      handleAttributeOpen={() => {}}
                      handleAttributeUpdate={() => {}}
                    />
                  </Box>
                }
              />
            )
          },
        }
      }),
    {
      id: 'tags',
      header: 'Tags',
      accessorKey: 'tags',
      size: 160,
      Cell: ({ cell }) => {
        const tagUids = cell.getValue() as string[] | undefined
        if (!tagUids) return null
        return tagUids
          .map((uid) =>
            tagsQuery.data ? tagsQuery.data.find((tag) => tag.uid === uid) : undefined,
          )
          .filter((tag): tag is Tag => tag !== undefined)
          .map((tag) => (
            <Tooltip key={tag.uid} title={tag.description ?? undefined}>
              <Chip
                label={tag.name}
                style={tag.color ? { backgroundColor: tag.color } : undefined}
              />
            </Tooltip>
          ))
      },
      filterVariant: 'multi-select' as const,
    },
  ]
  Object.entries(relationships).forEach((relation) => {
    const [id, definition] = relation
    columns.push({
      id: id,
      header: definition.title,
      accessorFn: (row) => row,
      filterVariant: 'range' as const,
      size: 130,

      Cell: ({ row }) => {
        const item = row.original
        const value = definition.valueGetter(item)
        if (value === 0) {
          return <Chip disabled label={value} />
        }
        return (
          <ValueActions
            value={`${value}`}
            quiet
            contentMinWidth={220}
            content={
              <ItemRelations relation={definition} item={item} onClick={onRowView} />
            }
          />
        )
      },
    })
  })

  const table = useMaterialReactTable({
    columns,
    data: itemsQuery.data?.items ?? [],
    state: {
      isLoading: itemsQuery.isLoading,
      showAlertBanner: itemsQuery.isError,
      showProgressBars: itemsQuery.isFetching,
      sorting: ownSorting,
      columnFilters: ownFilters,
      pagination,
    },
    initialState: { density: 'compact' },
    // Semantic layout hands leftover width to columns in proportion to their
    // content, so the identifier column started at a different offset in every
    // tab. In grid-no-grow each column takes exactly its size, and only the
    // attribute columns are marked to grow into what is left.
    layoutMode: 'grid-no-grow',
    displayColumnDefOptions: {
      'mrt-row-select': { size: 40, minSize: 40, maxSize: 40 },
    },
    manualFiltering: true,
    manualPagination: true,
    manualSorting: true,
    onColumnFiltersChange: handleColumnFiltersChange,
    onPaginationChange: setPagination,
    onSortingChange: handleSortingChange,
    rowCount: itemsQuery.data?.count ?? 0,
    enableRowSelection: rowsSelectable,
    // No actions column: the row's actions live in the identifier hover panel.
    enableRowActions: false,
    getRowId: (originalRow) => originalRow.uid,
    muiToolbarAlertBannerProps: itemsQuery.isError
      ? {
          color: 'error',
          children: 'Error loading data',
        }
      : undefined,
    renderTopToolbar: ({ table }) => {
      const selectedRowCount = table.getSelectedRowModel().rows.length
      return (
        <Box
          sx={(theme) => ({
            backgroundColor: lighten(theme.palette.background.default, 0.05),
            display: 'flex',
            gap: '0.5rem',
            p: '8px',
            justifyContent: 'space-between',
          })}
        >
          <Box>
            <Tooltip title="Toggle display of deleted items">
              <IconButton
                onClick={() => {
                  setDisplayOnlyInValid(false)
                  setDisplayRecycled(!displayRecycled)
                }}
                color={displayRecycled ? 'primary' : 'default'}
              >
                <Recycling />
              </IconButton>
            </Tooltip>
            <Tooltip title="Toggle display of invalid items">
              <IconButton
                onClick={() => {
                  setDisplayRecycled(false)
                  setDisplayOnlyInValid(!displayOnlyInValid)
                }}
                color={displayOnlyInValid ? 'primary' : 'default'}
              >
                <WarningTwoTone />
              </IconButton>
            </Tooltip>
          </Box>
          <Box sx={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <MRT_GlobalFilterTextField table={table} />
            <MRT_ToggleFiltersButton table={table} />
          </Box>
          <Box sx={{ display: 'flex', gap: '0.5rem' }}>
            {displayRecycled !== undefined && handleRowsState !== undefined && (
              // Says how many rows it is about to act on: it acts on the
              // selection rather than on a row the pointer is over, so what it
              // would take out of the project is not otherwise on screen.
              <Tooltip
                title={
                  selectedRowCount === 0
                    ? `Select rows to ${displayRecycled ? 'restore' : 'remove'}`
                    : `${displayRecycled ? 'Restore' : 'Remove'} ${selectedRowCount} selected ${
                        selectedRowCount === 1 ? 'item' : 'items'
                      } ${displayRecycled ? 'to' : 'from'} the project`
                }
              >
                <span>
                  <IconButton
                    disabled={selectedRowCount === 0}
                    onClick={(event) => handleRowsState(event.currentTarget)}
                    color={selectedRowCount === 0 ? 'default' : 'primary'}
                  >
                    {displayRecycled ? <RestoreFromTrash /> : <Delete />}
                  </IconButton>
                </span>
              </Tooltip>
            )}
            {onRowsRemap !== undefined && (
              <Tooltip title="Re-apply mappers to selected items">
                <span>
                  <IconButton
                    disabled={
                      !table.getIsSomeRowsSelected() && !table.getIsAllRowsSelected()
                    }
                    onClick={handleRowsRemap}
                    color={
                      !table.getIsSomeRowsSelected() && !table.getIsAllRowsSelected()
                        ? 'default'
                        : 'primary'
                    }
                  >
                    <AutoFixHigh />
                  </IconButton>
                </span>
              </Tooltip>
            )}

            {onRowsFlagForReview !== undefined && (
              <Tooltip title="Flag selected items for review">
                <span>
                  <IconButton
                    disabled={
                      !table.getIsSomeRowsSelected() && !table.getIsAllRowsSelected()
                    }
                    onClick={(event) => handleRowsFlagForReview(event.currentTarget)}
                    color={
                      !table.getIsSomeRowsSelected() && !table.getIsAllRowsSelected()
                        ? 'default'
                        : 'primary'
                    }
                  >
                    <OutlinedFlag />
                  </IconButton>
                </span>
              </Tooltip>
            )}

            {onRowsMarkReviewed !== undefined && (
              <Tooltip title="Mark selected items as reviewed">
                <span>
                  <IconButton
                    disabled={
                      !table.getIsSomeRowsSelected() && !table.getIsAllRowsSelected()
                    }
                    onClick={handleRowsMarkReviewed}
                    color={
                      !table.getIsSomeRowsSelected() && !table.getIsAllRowsSelected()
                        ? 'default'
                        : 'primary'
                    }
                  >
                    <Flag />
                  </IconButton>
                </span>
              </Tooltip>
            )}

            {onNew !== undefined && (
              <IconButton
                disabled={
                  !displayRecycled &&
                  (table.getIsSomeRowsSelected() || table.getIsAllRowsSelected())
                }
                onClick={handleNew}
                color={
                  !displayRecycled &&
                  (table.getIsSomeRowsSelected() || table.getIsAllRowsSelected())
                    ? 'default'
                    : 'primary'
                }
              >
                <Add />
              </IconButton>
            )}
          </Box>
        </Box>
      )
    },
  })
  return <MaterialReactTable table={table} />
}

interface ItemRelationProps {
  itemUid: string
  onClick: (itemUid: string) => void
}

function ItemRelation({ itemUid, onClick }: ItemRelationProps): React.ReactElement {
  const { pseudonymMode } = usePseudonym()
  const itemQuery = useQuery({
    queryKey: queryKeys.item.detail(itemUid),
    queryFn: async () => {
      return await itemApi.get(itemUid)
    },
  })
  if (itemQuery.isLoading) {
    return <CircularProgress />
  }
  if (itemQuery.data === undefined) {
    return <></>
  }
  return (
    <Chip
      label={getDisplayIdentifier(itemQuery.data, pseudonymMode)}
      onClick={() => onClick(itemQuery.data.uid)}
    />
  )
}

interface ItemRelationsProps {
  relation: RelationFilterDefinition
  item: Item
  onClick: (itemUid: string) => void
}

function ItemRelations({
  relation,
  item,
  onClick,
}: ItemRelationsProps): React.ReactElement {
  const getRelationItemUids = (item: Item): string[] => {
    if (isSampleItem(item)) {
      if (relation.relationType === RelationFilterType.CHILD) {
        return item.children[relation.relationSchemaUid]
      }
      if (relation.relationType === RelationFilterType.PARENT) {
        return item.parents[relation.relationSchemaUid]
      }
      if (relation.relationType === RelationFilterType.IMAGE) {
        return item.images[relation.relationSchemaUid]
      }
      if (relation.relationType === RelationFilterType.OBSERVATION) {
        return item.observations[relation.relationSchemaUid]
      }
    }
    if (isImageItem(item)) {
      if (relation.relationType === RelationFilterType.SAMPLE) {
        return item.samples[relation.relationSchemaUid]
      }
      if (relation.relationType === RelationFilterType.ANNOTATION) {
        return item.annotations[relation.relationSchemaUid]
      }
      if (relation.relationType === RelationFilterType.OBSERVATION) {
        return item.observations[relation.relationSchemaUid]
      }
    }
    if (isAnnotationItem(item)) {
      if (relation.relationType === RelationFilterType.OBSERVATION) {
        return item.observations[relation.relationSchemaUid]
      }
      if (relation.relationType === RelationFilterType.IMAGE) {
        if (item.image !== null && item.image[0] === relation.relationSchemaUid) {
          return [item.image[1]]
        }
      }
    }
    if (isObservationItem(item)) {
      if (relation.relationType === RelationFilterType.IMAGE) {
        if (item.image !== null && item.image[0] === relation.relationSchemaUid) {
          return [item.image[1]]
        }
      }
      if (relation.relationType === RelationFilterType.SAMPLE) {
        if (item.sample !== null && item.sample[0] === relation.relationSchemaUid) {
          return [item.sample[1]]
        }
      }
      if (relation.relationType === RelationFilterType.ANNOTATION) {
        if (
          item.annotation !== null &&
          item.annotation[0] === relation.relationSchemaUid
        ) {
          return [item.annotation[1]]
        }
      }
    }
    throw new Error(`Unknown relation type: ${relation.relationType}.`)
  }
  const relationItemUids = getRelationItemUids(item)
  return (
    <Stack spacing={1} direction={'column'}>
      {relationItemUids.map((uid) => (
        <ItemRelation key={uid} itemUid={uid} onClick={onClick} />
      ))}
    </Stack>
  )
}
