import React, { type ReactElement, useEffect, useState } from 'react'
import {
  MaterialReactTable,
  type MRT_ColumnDef,
  useMaterialReactTable,
  MRT_GlobalFilterTextField,
  MRT_ToggleFiltersButton,
} from 'material-react-table'
import {
  type ItemTableItem,
  type TableItem,
  Action,
  ActionStrings,
} from 'models/table_item'
import { Box, Button, MenuItem, lighten } from '@mui/material'
import { Delete, RestoreFromTrash, Edit, Add } from '@mui/icons-material'

interface AttributeTableProps {
  columns: Array<MRT_ColumnDef<any>>
  data: ItemTableItem[]
  rowsSelectable?: boolean
  isLoading: boolean
  displayRecycled: boolean
  onRowAction?: (itemUid: string, action: Action) => void
  onRowsStateChange?: (itemUids: string[], state: boolean) => void
  onRowsEdit?: (itemUids: string[]) => void
  onNew?: () => void
}

interface TableProps {
  columns: Array<MRT_ColumnDef<any>>
  data: TableItem[]
  rowsSelectable?: boolean
  isLoading?: boolean
  onRowAction?: (itemUid: string, action: Action) => void
}

export function AttributeTable({
  columns,
  data,
  rowsSelectable,
  isLoading,
  displayRecycled,
  onRowAction,
  onRowsStateChange,
  onRowsEdit,
  onNew,
}: AttributeTableProps): ReactElement {
  const actions = [
    Action.VIEW,
    Action.EDIT,
    displayRecycled ? Action.RESTORE : Action.DELETE,
    Action.COPY,
  ]
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
  const table = useMaterialReactTable({
    columns,
    data,
    state: { isLoading },
    initialState: { density: 'compact' },
    enableRowSelection: rowsSelectable,
    enableGlobalFilter: false,
    enableRowActions: true,
    positionActionsColumn: 'first',
    renderRowActionMenuItems: ({ row }) =>
      actions.map((action) => (
        <MenuItem
          key={action}
          onClick={() => {
            if (onRowAction === undefined) {
              return
            }
            const rowData = data[row.index]
            onRowAction(rowData.uid, action)
          }}
        >
          {ActionStrings[action]}
        </MenuItem>
      )),
    muiTableBodyRowProps: ({ row, table }) => ({
      onClick: (event) => {
        if (onRowAction !== undefined) {
          const rowData = data[row.index]
          onRowAction(rowData.uid, Action.VIEW)
        }
      },
    }),
    getRowId: (originalRow) => originalRow.uid,
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
          <Box sx={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <MRT_GlobalFilterTextField table={table} />
            <MRT_ToggleFiltersButton table={table} />
          </Box>
          <Box sx={{ display: 'flex', gap: '0.5rem' }}>
            {displayRecycled !== undefined && handleRowsState !== undefined && (
              <Button
                disabled={
                  !table.getIsSomeRowsSelected() && !table.getIsAllRowsSelected()
                }
                onClick={handleRowsState}
                variant="contained"
              >
                {displayRecycled ? <RestoreFromTrash /> : <Delete />}
              </Button>
            )}
            {onRowsEdit !== undefined && (
              <Button
                disabled={
                  !displayRecycled &&
                  !table.getIsSomeRowsSelected() &&
                  !table.getIsAllRowsSelected()
                }
                onClick={handleEdit}
                variant="contained"
              >
                <Edit />
              </Button>
            )}
            {onNew !== undefined && (
              <Button
                disabled={
                  !displayRecycled &&
                  (table.getIsSomeRowsSelected() || table.getIsAllRowsSelected())
                }
                onClick={handleNew}
                variant="contained"
              >
                <Add />
              </Button>
            )}
          </Box>
        </Box>
      )
    },
  })
  return <MaterialReactTable table={table} />
}

export function Table({
  columns,
  data,
  rowsSelectable,
  isLoading,
  onRowAction,
}: TableProps): ReactElement {
  const actions = [Action.VIEW, Action.EDIT]
  const table = useMaterialReactTable({
    columns,
    data,
    state: { isLoading },
    enableRowSelection: rowsSelectable,
    enableGlobalFilter: false,
    enableRowActions: true,
    positionActionsColumn: 'last',
    renderRowActionMenuItems: ({ row }) =>
      actions.map((action) => (
        <MenuItem
          key={action}
          onClick={() => {
            if (onRowAction === undefined) {
              return
            }
            const rowData = data[row.index]
            onRowAction(rowData.uid, action)
          }}
        >
          {ActionStrings[action]}
        </MenuItem>
      )),
    muiTableBodyRowProps: ({ row, table }) => ({
      onClick: (event) => {
        if (onRowAction !== undefined) {
          const rowData = data[row.index]
          onRowAction(rowData.uid, Action.VIEW)
        }
      },
    }),
  })
  return <MaterialReactTable table={table} />
}
