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

import { useEffect, useId, useMemo, useState, type ReactElement } from 'react'
import { FilterList, FilterListOff } from '@mui/icons-material'
import {
  Alert,
  Box,
  Checkbox,
  IconButton,
  LinearProgress,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Toolbar,
  Tooltip,
} from '@mui/material'
import { BodyCell } from './body/body_cell'
import { FilterInput } from './filters/filter_input'
import { HeadCell } from './head/head_cell'
import { PaginationBar } from './toolbar/pagination'
import type { DataTable } from './use_data_table'
import type { RowData } from './types'

/** Width of the leading checkbox column, and of the trailing actions column.
 *
 * Enough for a small checkbox and its padding, and no more: the gap that
 * separates it from the identifier beside it comes from the two cells' own
 * padding rather than from carrying dead width down every row. */
const SELECT_COLUMN_WIDTH = 48
const ACTIONS_COLUMN_WIDTH = 120

interface DataTableViewProps<T extends RowData> {
  table: DataTable<T>
}

/**
 * Draws a table built by `useDataTable`.
 *
 * Column widths are settled here rather than left to the browser: a column
 * without `grow` takes exactly its size, so the same column starts at the same
 * offset in every table that shows it, and only the columns marked to grow
 * share what is left over.
 */
export function DataTableView<T extends RowData>({
  table,
}: DataTableViewProps<T>): ReactElement {
  const { instance, columns, showSkeletons, isRefreshing, error, density, rowActions } =
    table
  const [showFilters, setShowFilters] = useState(false)
  // Which column the filter row was opened for. Opening the row is a render
  // away, so the box to put the cursor in does not exist yet at the moment it
  // is asked for.
  const [focusFilter, setFocusFilter] = useState<string | null>(null)
  const idPrefix = useId()

  const filterInputId = (columnId: string): string => `${idPrefix}filter-${columnId}`

  useEffect(() => {
    if (focusFilter === null || !showFilters) return
    document.getElementById(filterInputId(focusFilter))?.focus()
    setFocusFilter(null)
  })

  /** Show every filter box and put the cursor in this column's. */
  const filterByColumn = (columnId: string): void => {
    setShowFilters(true)
    setFocusFilter(columnId)
  }

  const filterable = columns.some((column) => column.filter !== undefined)
  const { selectable } = table

  const { widths, minTableWidth } = useMemo(() => {
    const growing = columns.filter((column) => column.grow === true)
    const fixed = columns.filter((column) => column.grow !== true)
    const fixedTotal = fixed.reduce((total, column) => total + (column.size ?? 180), 0)
    const chrome =
      (selectable ? SELECT_COLUMN_WIDTH : 0) +
      (rowActions !== undefined ? ACTIONS_COLUMN_WIDTH : 0)
    // What every column needs to keep the width it asked for. Below this the
    // table scrolls sideways rather than squeezing the columns: a fixed layout
    // asked for more room than it has scales every column down together, so a
    // wide row of attributes would take the identifier and the checkbox with
    // it and the whole table would be unreadable at once.
    const growMinimum = growing.reduce(
      (total, column) => total + (column.minSize ?? column.size ?? 180),
      0,
    )
    return {
      minTableWidth: fixedTotal + growMinimum + chrome,
      widths: new Map(
        columns.map((column) => [
          column.id,
          column.grow === true
            ? `calc((100% - ${fixedTotal + chrome}px) / ${growing.length})`
            : `${column.size ?? 180}px`,
        ]),
      ),
    }
  }, [columns, selectable, rowActions])

  const rows = instance.getRowModel().rows
  const pagination = instance.state.pagination ?? { pageIndex: 0, pageSize: 10 }
  const sorting = instance.state.sorting ?? []

  const sortDirectionOf = (columnId: string): 'asc' | 'desc' | false => {
    const entry = sorting.find((sort) => sort.id === columnId)
    if (entry === undefined) return false
    return entry.desc ? 'desc' : 'asc'
  }

  return (
    <Paper variant="outlined" sx={{ overflow: 'hidden' }}>
      <Toolbar variant="dense" disableGutters sx={{ px: 1, gap: 1 }}>
        {/* The slot hands its whole width to what the caller puts in it, so a
            toolbar that ranges its groups against each other — toggles at one
            end, actions at the other — has the room to do it. */}
        <Box
          sx={{
            flex: 1,
            minWidth: 0,
            display: 'flex',
            gap: 1,
            alignItems: 'center',
            '& > *': { flexGrow: 1, minWidth: 0 },
          }}
        >
          {table.toolbar}
        </Box>
        {filterable && (
          <Tooltip title={showFilters ? 'Hide filters' : 'Show filters'}>
            <IconButton
              size="small"
              onClick={() => setShowFilters((shown) => !shown)}
              aria-label={showFilters ? 'Hide filters' : 'Show filters'}
            >
              {showFilters ? <FilterListOff /> : <FilterList />}
            </IconButton>
          </Tooltip>
        )}
      </Toolbar>

      <Box sx={{ height: 4 }}>{isRefreshing && <LinearProgress />}</Box>

      {error !== null && (
        <Alert severity="error" sx={{ borderRadius: 0 }}>
          {error}
        </Alert>
      )}

      <TableContainer>
        <Table
          size={density === 'compact' ? 'small' : 'medium'}
          sx={{ tableLayout: 'fixed', minWidth: minTableWidth }}
        >
          <TableHead>
            <TableRow>
              {selectable && (
                // Not padding="checkbox": on a small table that sets a width
                // of 24 through a two-class rule that outranks anything given
                // here, and zeroes the box's own padding with it.
                <TableCell sx={{ width: SELECT_COLUMN_WIDTH, px: 1 }}>
                  {/* Page-scoped, because the box is on the page. Table-wide,
                      `getIsSomeRowsSelected` counts every tick still held for
                      rows that are not loaded, so it stays true with the page
                      fully ticked and the dash would sit there instead. */}
                  <Checkbox
                    size="small"
                    checked={instance.getIsAllPageRowsSelected()}
                    indeterminate={
                      instance.getIsSomePageRowsSelected() &&
                      !instance.getIsAllPageRowsSelected()
                    }
                    onChange={(event) =>
                      instance.toggleAllPageRowsSelected(event.target.checked)
                    }
                    slotProps={{
                      input: { 'aria-label': 'Select all rows on this page' },
                    }}
                  />
                </TableCell>
              )}
              {columns.map((column) => (
                <HeadCell
                  key={column.id}
                  column={column}
                  width={widths.get(column.id) ?? 'auto'}
                  sortDirection={sortDirectionOf(column.id)}
                  onToggleSort={() =>
                    instance.getColumn(column.id)?.toggleSorting(undefined, false)
                  }
                  onSort={(descending) =>
                    instance.getColumn(column.id)?.toggleSorting(descending, false)
                  }
                  onClearSort={() => instance.getColumn(column.id)?.clearSorting()}
                  showFilters={showFilters}
                  onFilterByColumn={() => filterByColumn(column.id)}
                  filterActive={
                    instance.getColumn(column.id)?.getFilterValue() !== undefined
                  }
                  filter={
                    column.filter === undefined ? null : (
                      <FilterInput
                        spec={column.filter}
                        inputId={filterInputId(column.id)}
                        label={column.header}
                        value={instance.getColumn(column.id)?.getFilterValue()}
                        onChange={(value) =>
                          instance.getColumn(column.id)?.setFilterValue(value)
                        }
                      />
                    )
                  }
                />
              ))}
              {rowActions !== undefined && (
                <TableCell sx={{ width: ACTIONS_COLUMN_WIDTH }} />
              )}
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.length === 0 && !showSkeletons && (
              <TableRow>
                <TableCell
                  colSpan={
                    columns.length +
                    (selectable ? 1 : 0) +
                    (rowActions !== undefined ? 1 : 0)
                  }
                  sx={{ textAlign: 'center', py: 4, opacity: 0.7 }}
                >
                  Nothing to show
                </TableCell>
              </TableRow>
            )}
            {rows.map((row) => (
              <TableRow key={row.id} hover selected={row.getIsSelected()}>
                {selectable && (
                  <TableCell sx={{ width: SELECT_COLUMN_WIDTH, px: 1 }}>
                    <Checkbox
                      size="small"
                      checked={row.getIsSelected()}
                      disabled={!row.getCanSelect()}
                      onChange={(event) => row.toggleSelected(event.target.checked)}
                      slotProps={{ input: { 'aria-label': 'Select row' } }}
                    />
                  </TableCell>
                )}
                {columns.map((column) => (
                  <BodyCell
                    key={column.id}
                    column={column}
                    row={row.original}
                    value={row.getValue(column.id)}
                    skeleton={showSkeletons}
                    density={density}
                    width={widths.get(column.id) ?? 'auto'}
                  />
                ))}
                {rowActions !== undefined && (
                  <TableCell sx={{ width: ACTIONS_COLUMN_WIDTH }}>
                    {showSkeletons ? null : rowActions(row.original)}
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <PaginationBar
        pagination={pagination}
        rowCount={table.rowCount}
        pending={showSkeletons}
        onChange={(next) => instance.setPagination(next)}
      />
    </Paper>
  )
}
