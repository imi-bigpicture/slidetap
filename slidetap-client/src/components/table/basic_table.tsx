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

import { Box } from '@mui/material'
import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
} from 'material-react-table'
import React, { ReactElement } from 'react'
import { Action, ActionStrings } from 'src/models/action'
import ActionsIcons from './action_icons'
import { cellCopyOptions } from './table_interaction'
import { withValueActionsColumn } from './value_actions'

interface BasicTableProps<T extends { uid: string }> {
  columns: Array<MRT_ColumnDef<T>>
  data: T[]
  rowsSelectable?: boolean
  isLoading?: boolean
  actions?: {
    action: Action
    onAction: (item: T) => void
    enabled?: (item: T) => boolean
    inMenu?: boolean
  }[]
  topBarActions?: ReactElement[]
}

export function BasicTable<T extends { uid: string }>({
  columns,
  data,
  rowsSelectable,
  isLoading,
  actions,
  topBarActions,
}: BasicTableProps<T>): React.ReactElement {
  const firstColumnId =
    columns[0]?.id ?? columns[0]?.accessorKey?.toString() ?? ''
  const panelColumns = React.useMemo(
    () =>
      withValueActionsColumn<T>(
        columns,
        (row) => String(row.getValue(firstColumnId) ?? ''),
        (row) => {
          const view = actions?.find(
            (action) =>
              action.action === Action.VIEW && (action.enabled?.(row.original) ?? true),
          )
          return view && (() => view.onAction(row.original))
        },
        (row) =>
          (actions ?? [])
            .filter((action) => action.action !== Action.VIEW)
            .map((action) => ({
              key: `${action.action}`,
              icon: ActionsIcons[action.action],
              label: ActionStrings[action.action],
              onClick: () => action.onAction(row.original),
              disabled: action.enabled !== undefined && !action.enabled(row.original),
            })),
      ),
    [columns, firstColumnId, actions],
  )
  const table = useMaterialReactTable({
    columns: panelColumns,
    data,
    ...cellCopyOptions,
    state: {
      showSkeletons: false,
      showLoadingOverlay: false,
      showProgressBars: isLoading,
    },
    initialState: {
      showColumnFilters: true,
      sorting: [
        {
          id: columns[0]?.id ?? columns[0]?.accessorKey?.toString() ?? '',
          desc: false,
        },
      ],
    },
    enableRowSelection: rowsSelectable,
    enableGlobalFilter: false,
    // No actions column: the row's actions live in the first column's panel.
    enableRowActions: false,
    renderTopToolbarCustomActions: () => (
      <Box sx={{ display: 'flex', gap: '1rem', p: '4px' }}>{topBarActions}</Box>
    ),
  })
  return <MaterialReactTable table={table} />
}
