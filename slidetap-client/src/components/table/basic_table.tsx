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
import { Action } from 'src/models/action'
import RowActions from './row_actions'

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
  const table = useMaterialReactTable({
    columns,
    data,
    state: {
      showSkeletons: false,
      showLoadingOverlay: false,
      showProgressBars: isLoading,
    },
    initialState: {
      sorting: [
        {
          id: columns[0].id ?? '',
          desc: false,
        },
      ],
    },
    enableRowSelection: rowsSelectable,
    enableGlobalFilter: false,
    enableRowActions: true,
    positionActionsColumn: 'last',
    renderRowActions: ({ row }) => <RowActions row={row} actions={actions} />,
    renderTopToolbarCustomActions: () => (
      <Box sx={{ display: 'flex', gap: '1rem', p: '4px' }}>{topBarActions}</Box>
    ),
  })
  return <MaterialReactTable table={table} />
}
