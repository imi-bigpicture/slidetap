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

import { Replay } from '@mui/icons-material'
import { Box, IconButton, MenuItem, lighten } from '@mui/material'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import {
  MRT_GlobalFilterTextField,
  MRT_ToggleFiltersButton,
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
  type MRT_ColumnFiltersState,
  type MRT_PaginationState,
  type MRT_SortingState,
} from 'material-react-table'
import {
  ImageAction,
  ImageRedoProcessingActionStrings as ImageActionStrings,
} from 'models/action'
import { ImageStatus } from 'models/image_status'
import type { ColumnFilter, ColumnSort, TableItem } from 'models/table_item'
import React, { useState } from 'react'

interface ImageTableProps {
  getItems: (
    start: number,
    size: number,
    filters: ColumnFilter[],
    sorting: ColumnSort[],
  ) => Promise<{ items: TableItem[]; count: number }>
  columns: Array<MRT_ColumnDef<any>>
  rowsSelectable?: boolean
  onRowAction?: (itemUid: string, action: ImageAction) => void
  onRowsRetry?: (itemUids: string[]) => void
}

export function ImageTable({
  getItems,
  columns,
  rowsSelectable,
  onRowAction,
  onRowsRetry,
}: ImageTableProps): React.ReactElement {
  const [columnFilters, setColumnFilters] = useState<MRT_ColumnFiltersState>([])
  const [sorting, setSorting] = useState<MRT_SortingState>([])
  const [pagination, setPagination] = useState<MRT_PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  })
  const imagesQuery = useQuery({
    queryKey: [
      'images',
      pagination.pageIndex,
      pagination.pageSize,
      columnFilters,
      sorting,
    ],
    queryFn: async () => {
      return await getItems(
        pagination.pageIndex * pagination.pageSize,
        pagination.pageSize,
        columnFilters,
        sorting.map((sort) => {
          let isAttribute = true
          let column = ''
          if (sort.id === 'id') {
            column = 'identifier'
            isAttribute = false
          } else if (sort.id === 'valid') {
            column = 'valid'
            isAttribute = false
          } else if (sort.id === 'status') {
            column = 'status'
            isAttribute = false
          } else if (sort.id === 'message') {
            column = 'statusMessage'
            isAttribute = false
          } else {
            column = sort.id.split('attributes.')[1]
            isAttribute = true
          }
          return { column, isAttribute, descending: sort.desc }
        }),
      )
    },
    // refetchInterval: 2000,
    placeholderData: keepPreviousData,
  })
  const handleRetry = (): void => {
    onRowsRetry?.(table.getSelectedRowModel().flatRows.map((row) => row.id))
  }

  const table = useMaterialReactTable({
    columns,
    data: imagesQuery.data?.items ?? [],
    state: {
      isLoading: imagesQuery.isLoading,
      showAlertBanner: imagesQuery.isError,
      showProgressBars: imagesQuery.isRefetching,
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
    rowCount: imagesQuery.data?.count ?? 0,
    enableRowSelection: rowsSelectable,
    enableRowActions: true,
    positionActionsColumn: 'first',
    renderRowActionMenuItems: ({ row }) => {
      const rowActions = [ImageAction.VIEW, ImageAction.EDIT]
      const status = row.original.status
      if (
        status === ImageStatus.DOWNLOADING_FAILED ||
        status === ImageStatus.PRE_PROCESSING_FAILED ||
        status === ImageStatus.POST_PROCESSING_FAILED
      ) {
        rowActions.push(ImageAction.RETRY)
      }
      return rowActions.map((action) => (
        <MenuItem
          key={action}
          onClick={() => {
            if (onRowAction === undefined) {
              return
            }
            onRowAction(row.original.uid, action)
          }}
        >
          {ImageActionStrings[action]}
        </MenuItem>
      ))
    },
    muiTableBodyRowProps: ({ row, table }) => ({
      onClick: (event) => {
        if (imagesQuery.data !== undefined && onRowAction !== undefined) {
          const rowData = imagesQuery.data?.items[row.index]
          onRowAction(rowData.uid, ImageAction.VIEW)
        }
      },
    }),
    getRowId: (originalRow) => originalRow.uid,
    muiToolbarAlertBannerProps: imagesQuery.isError
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
          <Box></Box>
          <Box sx={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <MRT_GlobalFilterTextField table={table} />
            <MRT_ToggleFiltersButton table={table} />
          </Box>
          <Box sx={{ display: 'flex', gap: '0.5rem' }}>
            {onRowsRetry !== undefined && (
              <IconButton
                disabled={
                  !table.getIsSomeRowsSelected() && !table.getIsAllRowsSelected()
                }
                onClick={handleRetry}
                color={
                  !table.getIsSomeRowsSelected() && !table.getIsAllRowsSelected()
                    ? 'default'
                    : 'primary'
                }
              >
                <Replay />
              </IconButton>
            )}
          </Box>
        </Box>
      )
    },
  })
  return <MaterialReactTable table={table} />
}
