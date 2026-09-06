//    Copyright 2026 SECTRA AB
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

import React, { type ReactElement } from 'react'
import { Box } from '@mui/material'
import { Action, ActionStrings } from 'src/models/action'
import ActionsIcons from './action_icons'
import { ValueActions } from './value_actions'
import {
  DataTableView,
  useDataTable,
  type ColumnDef,
  type ToolbarContext,
} from './data_table'

interface BasicDataTableProps<T extends { uid: string }> {
  columns: Array<ColumnDef<T>>
  data: T[]
  rowsSelectable?: boolean
  isLoading?: boolean
  actions?: Array<{
    action: Action
    onAction: (item: T) => void
    enabled?: (item: T) => boolean
  }>
  /** Buttons above the table.
   *
   * Given what is shown where that matters: the rows the reader is looking at,
   * filtered and sorted. Passing plain elements is still the usual case. */
  topBarActions?: ReactElement[] | ((context: ToolbarContext<T>) => ReactElement[])
}

/**
 * A table of things the caller already has, all of them, with the row's actions
 * on the chip in its first column.
 *
 * No paging against a server and no filtering it has to be asked for: this is
 * for lists short enough to hold, which is what lets sorting and filtering be
 * done here rather than round-tripped.
 */
export function BasicDataTable<T extends { uid: string }>({
  columns,
  data,
  rowsSelectable,
  isLoading,
  actions,
  topBarActions,
}: BasicDataTableProps<T>): ReactElement {
  const firstColumnId = columns[0]?.id ?? ''

  // The row's actions live on the first column's chip rather than in a column
  // of their own, so a narrow table is not mostly buttons.
  const panelColumns = React.useMemo<Array<ColumnDef<T>>>(() => {
    const [first, ...rest] = columns
    if (first === undefined) return columns
    return [
      {
        ...first,
        Cell: ({ row, value }) => {
          const view = actions?.find(
            (candidate) =>
              candidate.action === Action.VIEW && (candidate.enabled?.(row) ?? true),
          )
          return (
            <ValueActions
              // The same height as every other chip in the row, so the value
              // and the status beside it read as one line rather than two
              // sizes.
              dense
              value={String(value ?? '')}
              onOpen={view && (() => view.onAction(row))}
              actions={(actions ?? [])
                .filter((candidate) => candidate.action !== Action.VIEW)
                .map((candidate) => ({
                  key: `${candidate.action}`,
                  icon: ActionsIcons[candidate.action],
                  label: ActionStrings[candidate.action],
                  onClick: () => candidate.onAction(row),
                  disabled: candidate.enabled !== undefined && !candidate.enabled(row),
                }))}
              copyable
              copyLabel="Copy name"
            />
          )
        },
      },
      ...rest,
    ]
  }, [columns, actions])

  const table = useDataTable<T>({
    columns: panelColumns,
    data,
    getRowId: (row) => row.uid,
    load: isLoading === true ? { status: 'loading' } : { status: 'ready' },
    selection: rowsSelectable === true ? {} : undefined,
    defaultSort:
      firstColumnId === '' ? undefined : { id: firstColumnId, descending: false },
    toolbar: (context) => (
      <Box sx={{ display: 'flex', gap: '1rem', p: '4px' }}>
        {typeof topBarActions === 'function' ? topBarActions(context) : topBarActions}
      </Box>
    ),
  })

  return <DataTableView table={table} />
}
