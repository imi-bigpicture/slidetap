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

import { MenuItem } from '@mui/material'
import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
} from 'material-react-table'
import { Action, ActionStrings } from 'models/action'
import type { TableItem } from 'models/table_item'
import React from 'react'

interface BasicTableProps {
  columns: Array<MRT_ColumnDef<any>>
  data: TableItem[]
  rowsSelectable?: boolean
  isLoading?: boolean
  onRowAction?: (itemUid: string, action: Action) => void
}

export function BasicTable({
  columns,
  data,
  rowsSelectable,
  isLoading,
  onRowAction,
}: BasicTableProps): React.ReactElement {
  const actions = [Action.VIEW, Action.EDIT]
  const table = useMaterialReactTable({
    columns,
    data,
    state: {
      showSkeletons: false,
      showLoadingOverlay: false,
      showProgressBars: isLoading,
    },
    enableRowSelection: rowsSelectable,
    enableGlobalFilter: false,
    enableRowActions: true,
    positionActionsColumn: 'last',
    renderRowActionMenuItems: ({ closeMenu, row }) =>
      actions.map((action) => (
        <MenuItem
          key={action}
          onClick={() => {
            if (onRowAction === undefined) {
              return
            }
            const rowData = data[row.index]
            onRowAction(rowData.uid, action)
            closeMenu()
          }}
        >
          {ActionStrings[action]}
        </MenuItem>
      )),
  })
  return <MaterialReactTable table={table} />
}
