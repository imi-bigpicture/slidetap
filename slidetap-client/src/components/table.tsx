import React, { type ReactElement, useEffect, useState } from 'react'
import {
  MaterialReactTable,
  type MRT_RowSelectionState,
  type MRT_ColumnDef,
} from 'material-react-table'
import {
  type ItemTableItem,
  type TableItem,
  Action,
  ActionStrings,
} from 'models/table_item'
import { MenuItem } from '@mui/material'

interface AttributeTableProps {
  columns: Array<MRT_ColumnDef<any>>
  data: ItemTableItem[]
  rowsSelectable?: boolean
  isLoading?: boolean
  onRowAction?: (itemUid: string, action: Action) => void
  onRowSelect?: (itemUid: string, value: boolean) => void
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
  onRowAction,
  onRowSelect,
}: AttributeTableProps): ReactElement {
  const [rowSelection, setRowSelection] = useState<MRT_RowSelectionState>({})

  useEffect(() => {
    const getRowSelection = (data: ItemTableItem[]): Record<string, boolean> => {
      const selection = Object.fromEntries(
        data.map((item) => [item.uid, item.selected]),
      )
      return selection
    }
    setRowSelection(getRowSelection(data))
  }, [data])
  const actions = [Action.VIEW, Action.EDIT]
  return (
    <MaterialReactTable
      columns={columns}
      data={data}
      state={{ isLoading, rowSelection }}
      initialState={{ density: 'compact' }}
      enableRowSelection={rowsSelectable}
      enableGlobalFilter={false}
      enableRowActions={true}
      positionActionsColumn="last"
      renderRowActionMenuItems={({ row }) =>
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
        ))
      }
      onRowSelectionChange={setRowSelection}
      muiTableBodyRowProps={({ row, table }) => ({
        onClick: (event) => {
          if (onRowAction !== undefined) {
            const rowData = data[row.index]
            onRowAction(rowData.uid, Action.VIEW)
          }
        },
      })}
      muiSelectCheckboxProps={({ row, table }) => ({
        onClick: (event) => {
          if (onRowSelect === undefined) {
            return
          }
          onRowSelect(row.id, !row.getIsSelected())
        },
      })}
      muiSelectAllCheckboxProps={({ table }) => ({
        onClick: (event) => {
          if (onRowSelect === undefined) {
            return
          }
          const rowIds = Object.keys(table.getRowModel().rowsById)
          const selectionState = !table.getIsAllRowsSelected()
          rowIds.forEach((itemUid) => {
            onRowSelect(itemUid, selectionState)
          })
        },
      })}
      getRowId={(originalRow) => originalRow.uid}
    />
  )
}

export function Table({
  columns,
  data,
  rowsSelectable,
  isLoading,
  onRowAction,
}: TableProps): ReactElement {
  const actions = [Action.VIEW, Action.EDIT]

  return (
    <MaterialReactTable
      columns={columns}
      data={data}
      state={{ isLoading }}
      enableRowSelection={rowsSelectable}
      enableGlobalFilter={false}
      enableRowActions={true}
      positionActionsColumn="last"
      renderRowActionMenuItems={({ row }) =>
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
        ))
      }
      muiTableBodyRowProps={({ row, table }) => ({
        onClick: (event) => {
          if (onRowAction !== undefined) {
            const rowData = data[row.index]
            onRowAction(rowData.uid, Action.VIEW)
          }
        },
      })}
    />
  )
}
