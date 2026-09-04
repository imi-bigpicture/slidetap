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

import type { ReactElement } from 'react'
import { Box, Skeleton, TableCell } from '@mui/material'
import type { ColumnDef, RowData } from '../types'

interface BodyCellProps<T extends RowData> {
  column: ColumnDef<T>
  row: T
  value: unknown
  /** The row is a blank standing in for one still being loaded. */
  skeleton: boolean
  density: 'compact' | 'comfortable'
  width: string
}

/**
 * One cell.
 *
 * While the table is loading, its rows are blanks shaped by the columns rather
 * than by the caller's data, so a skeleton is drawn and the caller's `Cell` is
 * never called: it would be handed a row that is not one of its own.
 */
export function BodyCell<T extends RowData>({
  column,
  row,
  value,
  skeleton,
  density,
  width,
}: BodyCellProps<T>): ReactElement {
  const Cell = column.Cell
  return (
    <TableCell
      sx={{
        width,
        px: 1,
        py: density === 'compact' ? 0.4 : 1,
      }}
    >
      {skeleton ? (
        <Skeleton animation="wave" height={20} />
      ) : Cell !== undefined ? (
        // Called rather than rendered as a component of its own. Callers build
        // their columns inline, so `Cell` is a new function on every render;
        // as an element type that reads as a different component each time and
        // React throws the cell away and builds it again, taking with it the
        // identifier panel's open state and the queries inside it — on a table
        // that polls every two seconds, continuously. Calling it makes the
        // identity churn harmless, at the cost of the rule on `ColumnDef.Cell`.
        //
        // Drawn without clipping: what a column draws for itself sizes itself,
        // and the identifier chip is drawn over by a panel that grows out of
        // it, which would read as appearing beside the value rather than out
        // of it if the chip were cut to the column.
        Cell({ row, value })
      ) : (
        // Plain values are held to the column, which is what the fixed layout
        // is for: a long one is cut with an ellipsis rather than pushing the
        // columns after it out of line.
        <Box
          sx={{
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {formatValue(value)}
        </Box>
      )}
    </TableCell>
  )
}

/** What a cell shows when the column does not say how to render it. */
function formatValue(value: unknown): string {
  if (value === null || value === undefined) return ''
  if (Array.isArray(value)) return value.join(', ')
  if (value instanceof Date) return value.toLocaleDateString()
  if (typeof value === 'object') return ''
  return String(value)
}
