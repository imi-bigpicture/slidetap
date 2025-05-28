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
  Delete,
  Done,
  Edit,
  PriorityHigh,
  Recycling,
  RestoreFromTrash,
  WarningTwoTone,
} from '@mui/icons-material'
import { Box, IconButton, Tooltip, lighten } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import {
  MRT_GlobalFilterTextField,
  MRT_ToggleFiltersButton,
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_Cell,
  type MRT_ColumnFiltersState,
  type MRT_PaginationState,
  type MRT_SortingState,
} from 'material-react-table'
import React, { useState } from 'react'
import { Action } from 'src/models/action'
import { Item } from 'src/models/item'
import type { ItemSchema } from 'src/models/schema/item_schema'
import type { ColumnFilter, ColumnSort } from 'src/models/table_item'
import RowActions from './row_actions'

interface ItemTableProps {
  getItems: (
    schemaUid: string,
    start: number,
    size: number,
    filters: ColumnFilter[],
    sorting: ColumnSort[],
    recycled?: boolean,
    invalid?: boolean,
  ) => Promise<{ items: Item[]; count: number }>
  schema: ItemSchema
  rowsSelectable?: boolean
  actions?: {
    action: Action
    onAction: (item: Item) => void
    enabled?: (item: Item) => boolean
    inMenu?: boolean
  }[]
  onRowsStateChange?: (itemUids: string[], state: boolean) => void
  onRowsEdit?: (itemUids: string[]) => void
  onNew?: () => void
  refresh: boolean
}

export function ItemTable({
  getItems,
  schema,
  rowsSelectable,
  actions,
  onRowsStateChange,
  onRowsEdit,
  onNew,
  refresh,
}: ItemTableProps): React.ReactElement {
  const [columnFilters, setColumnFilters] = useState<MRT_ColumnFiltersState>([])
  const [sorting, setSorting] = useState<MRT_SortingState>([])
  const [pagination, setPagination] = useState<MRT_PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  })
  const [displayRecycled, setDisplayRecycled] = useState(false)
  const [displayOnlyInValid, setDisplayOnlyInValid] = useState(false)
  const attributeQuery = useQuery({
    queryKey: [
      'attributes',
      schema.uid,
      columnFilters,
      sorting,
      pagination,
      displayRecycled,
      displayOnlyInValid,
    ],
    queryFn: async () => {
      return await getItems(
        schema.uid,
        pagination.pageIndex * pagination.pageSize,
        pagination.pageSize,
        columnFilters,
        sorting.map((sort) => {
          if (sort.id === 'id') {
            return { column: 'identifier', isAttribute: false, descending: sort.desc }
          }
          if (sort.id === 'valid') {
            return { column: 'valid', isAttribute: false, descending: sort.desc }
          }
          return {
            column: sort.id.split('attributes.')[1],
            isAttribute: true,
            descending: sort.desc,
          }
        }),
        displayRecycled,
        displayOnlyInValid ? true : undefined,
      )
    },
    refetchInterval: refresh ? 2000 : false,
  })

  const handleRowsState = (): void => {
    if (displayRecycled === undefined) {
      return
    }
    onRowsStateChange?.(
      table.getSelectedRowModel().flatRows.map((row) => row.id),
      displayRecycled,
    )
  }

  const handleNew = (): void => {
    onNew?.()
  }

  const handleEdit = (): void => {
    onRowsEdit?.(table.getSelectedRowModel().flatRows.map((row) => row.id))
  }
  const columns = [
    { id: 'id', header: 'Id', accessorKey: 'identifier' },
    {
      id: 'valid',
      header: 'Valid',
      accessorKey: 'valid',
      Cell: (props: { cell: MRT_Cell<Item, unknown> }) =>
        props.cell.getValue<boolean>() ? (
          <Done color="success" />
        ) : (
          <PriorityHigh color="warning" />
        ),
    },
    ...Object.values(schema.attributes)
      .filter((attributeSchema) => attributeSchema.displayInTable)
      .map((attributeSchema) => {
        return {
          header: attributeSchema.displayName,
          accessorKey: `attributes.${attributeSchema.tag}.displayValue`,
          id: `attributes.${attributeSchema.tag}`,
        }
      }),
  ]
  const table = useMaterialReactTable({
    columns,
    data: attributeQuery.data?.items ?? [],
    state: {
      isLoading: attributeQuery.isLoading,
      showAlertBanner: attributeQuery.isError,
      showProgressBars: attributeQuery.isFetching,
      sorting,
      columnFilters,
      pagination,
    },
    initialState: { density: 'compact' },
    manualFiltering: true,
    manualPagination: true,
    manualSorting: true,
    onColumnFiltersChange: setColumnFilters,
    onPaginationChange: setPagination,
    onSortingChange: setSorting,
    rowCount: attributeQuery.data?.count ?? 0,
    enableRowSelection: rowsSelectable,
    enableRowActions: true,
    positionActionsColumn: 'last',
    renderRowActions: ({ row }) => {
      return <RowActions row={row} actions={actions} displayRestore={displayRecycled} />
    },
    getRowId: (originalRow) => originalRow.uid,
    muiToolbarAlertBannerProps: attributeQuery.isError
      ? {
          color: 'error',
          children: 'Error loading data',
        }
      : undefined,
    renderTopToolbar: ({ table }) => {
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
              <IconButton
                disabled={
                  !table.getIsSomeRowsSelected() && !table.getIsAllRowsSelected()
                }
                onClick={handleRowsState}
                color={
                  !table.getIsSomeRowsSelected() && !table.getIsAllRowsSelected()
                    ? 'default'
                    : 'primary'
                }
              >
                {displayRecycled ? <RestoreFromTrash /> : <Delete />}
              </IconButton>
            )}
            {onRowsEdit !== undefined && (
              <IconButton
                disabled={
                  !displayRecycled &&
                  !table.getIsSomeRowsSelected() &&
                  !table.getIsAllRowsSelected()
                }
                onClick={handleEdit}
                color={
                  !displayRecycled &&
                  !table.getIsSomeRowsSelected() &&
                  !table.getIsAllRowsSelected()
                    ? 'default'
                    : 'primary'
                }
              >
                <Edit />
              </IconButton>
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
