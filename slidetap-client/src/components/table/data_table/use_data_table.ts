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

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import {
  functionalUpdate,
  useTable,
  type ColumnDef as TanStackColumnDef,
  type ReactTable,
  type RowSelectionState,
  type Updater,
} from '@tanstack/react-table'
import { tableFeatureBundle } from './features'
import { filterFor } from './filters/filter_fns'
import type {
  ColumnDef,
  ColumnFiltersState,
  DataTableOptions,
  PaginationState,
  FilterSpec,
  RowData,
  SortingState,
  TableRow,
} from './types'

/** How many blank rows stand in for a page that has not arrived. */
const SKELETON_ROWS = 10

export interface DataTable<T extends RowData> {
  instance: ReactTable<typeof tableFeatureBundle, T>
  columns: Array<ColumnDef<T>>
  /** True while the rows on screen are blanks waiting for real ones. */
  showSkeletons: boolean
  isRefreshing: boolean
  error: string | null
  rowCount: number
  /** The table has a checkbox column, whether or not its rows can be ticked
   * yet. */
  selectable: boolean
  density: 'compact' | 'comfortable'
  rowActions?: (row: T) => ReactNode
  /** Already rendered, with the selection the toolbar asked about. */
  toolbar: ReactNode
}

/**
 * Reads what a caller asks for into a TanStack table.
 *
 * The blank rows a loading table shows are made here rather than by the caller,
 * because they have to be shaped by the columns: a row of the caller's own type
 * cannot be invented without inventing its contents.
 */
export function useDataTable<T extends RowData>(
  options: DataTableOptions<T>,
): DataTable<T> {
  const {
    columns,
    data,
    getRowId,
    load,
    server,
    selection,
    rowActions,
    density = 'comfortable',
    defaultSort,
  } = options

  const showSkeletons = load.status === 'loading'

  // A blank row carries the column ids and nothing else. It never reaches a
  // caller's `Cell`, which is only rendered once real rows have arrived.
  const skeletonRows = useMemo(() => {
    if (!showSkeletons) return null
    const blank = Object.fromEntries(columns.map((column) => [column.id, null]))
    return Array.from({ length: SKELETON_ROWS }, (_, index) => ({
      ...blank,
      __skeletonId: `skeleton-${index}`,
    })) as unknown as T[]
  }, [showSkeletons, columns])

  const rows = skeletonRows ?? data

  const tanstackColumns = useMemo<
    Array<TanStackColumnDef<typeof tableFeatureBundle, T>>
  >(
    () =>
      columns.map((column) => {
        const accessor =
          column.accessorFn ??
          (column.accessorKey !== undefined
            ? readPath<T>(column.accessorKey)
            : () => undefined)
        return {
          id: column.id,
          header: column.header,
          accessorFn: accessor,
          size: column.size,
          minSize: column.minSize,
          enableSorting: column.sortable ?? true,
          enableColumnFilter: column.filter !== undefined,
          // Named rather than left to `'auto'`, which picks by the type of the
          // value in the cell and so cannot know what shape the filter above it
          // produces. A status column of numbers picked from a list would
          // otherwise be read as a numeric range.
          filterFn:
            column.filter === undefined
              ? undefined
              : (row: TableRow<T>, columnId: string, filterValue: unknown) =>
                  filterFor(column.filter as FilterSpec)(
                    row.getValue(columnId),
                    filterValue,
                  ),
        } as TanStackColumnDef<typeof tableFeatureBundle, T>
      }),
    [columns],
  )

  // Selection and, for a table that holds all its rows, filtering and sorting
  // are kept here. A server-side table is given them instead.
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({})
  const [ownFilters, setOwnFilters] = useState<ColumnFiltersState>([])
  const [ownSorting, setOwnSorting] = useState<SortingState>(
    defaultSort ? [{ id: defaultSort.id, desc: defaultSort.descending }] : [],
  )
  const [ownPagination, setOwnPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  })

  const filters = server?.filters ?? ownFilters
  const sorting = server?.sorting ?? ownSorting
  const pagination = server?.pagination ?? ownPagination

  const applyFilters = useCallback(
    (updater: Updater<ColumnFiltersState>) => {
      const next = functionalUpdate(updater, filters)
      if (server) server.onFiltersChange(next)
      else setOwnFilters(next)
    },
    [server, filters],
  )

  const applySorting = useCallback(
    (updater: Updater<SortingState>) => {
      const next = functionalUpdate(updater, sorting)
      if (server) server.onSortingChange(next)
      else setOwnSorting(next)
    },
    [server, sorting],
  )

  const applyPagination = useCallback(
    (updater: Updater<PaginationState>) => {
      const next = functionalUpdate(updater, pagination)
      if (server) server.onPaginationChange(next)
      else setOwnPagination(next)
    },
    [server, pagination],
  )

  const instance = useTable<typeof tableFeatureBundle, T>({
    features: tableFeatureBundle,
    columns: tanstackColumns,
    data: rows,
    // A blank row has no identity of the caller's kind, so it is keyed by the
    // stand-in id given above rather than by asking the caller for one.
    getRowId: showSkeletons
      ? (row) => (row as { __skeletonId: string }).__skeletonId
      : getRowId,
    manualFiltering: server !== undefined,
    manualSorting: server !== undefined,
    manualPagination: server !== undefined,
    // Only where the server is counting. Given for a table that holds its own
    // rows it would override the count after filtering, and the pager would
    // offer pages of rows the filter had already removed.
    rowCount: server?.rowCount,
    // On for the table whenever the caller asked for it, and refused row by
    // row while the rows are blanks. Turning it off wholesale would take the
    // checkbox column away with it, and every other column would step across
    // by its width the moment the first page landed.
    enableRowSelection: selection === undefined ? false : () => !showSkeletons,
    state: { columnFilters: filters, sorting, pagination, rowSelection },
    onColumnFiltersChange: applyFilters,
    onSortingChange: applySorting,
    onPaginationChange: applyPagination,
    onRowSelectionChange: (updater: Updater<RowSelectionState>) => {
      setRowSelection(functionalUpdate(updater, rowSelection))
    },
  })

  const visibleRows = instance.getRowModel().rows

  // Only rows that are actually here.
  //
  // A tick survives in `rowSelection` after its row has gone — turned a page,
  // narrowed a filter, or refetched without it — and acting on those would send
  // away identifiers nobody can see. The ticks are kept rather than cleared, so
  // paging back finds the selection intact; it is the acting on them that is
  // held to what is loaded.
  //
  // Not memoized on `visibleRows`: the row model is cached on the data alone,
  // so ticking a box hands back the same array and a memo keyed on it would
  // answer with the selection from before the tick.
  const selectedRows = visibleRows.filter((row) => row.getIsSelected())
  const selectedRowIds = selectedRows.map((row) => row.id)

  // Reported after render rather than during, so a caller storing the selection
  // does not set state while this one is still rendering.
  //
  // The key is only how the effect notices a change; what it hands over is the
  // list itself. Rebuilding the ids by splitting the key would tear any id
  // holding the separator, and `unmapped` already keys its rows on attribute
  // values a pathologist wrote.
  const notifySelection = selection?.onChange
  const selectionKey = JSON.stringify(selectedRowIds)
  const latestSelection = useRef(selectedRowIds)
  latestSelection.current = selectedRowIds
  const lastReported = useRef<string>('[]')
  useEffect(() => {
    if (notifySelection === undefined) return
    if (selectionKey === lastReported.current) return
    lastReported.current = selectionKey
    notifySelection(latestSelection.current)
  }, [selectionKey, notifySelection])

  const toolbar =
    options.toolbar?.({
      // Everything the filters left, not the page being looked at: a toolbar
      // acting on what is shown means what the reader narrowed it to.
      rows: showSkeletons
        ? []
        : instance.getPrePaginatedRowModel().rows.map((row) => row.original),
      selectedRowIds,
      selectedRows: selectedRows.map((row) => row.original),
      clearSelection: () => setRowSelection({}),
    }) ?? null

  return {
    instance,
    columns,
    toolbar,
    showSkeletons,
    isRefreshing: load.status === 'refreshing',
    error: load.status === 'error' ? load.message : null,
    rowCount: server ? server.rowCount : instance.getPrePaginatedRowModel().rows.length,
    selectable: selection !== undefined,
    density,
    rowActions,
  }
}

/** Reads a dotted key off a row, giving up quietly on a missing step. */
function readPath<T extends RowData>(key: string): (row: T) => unknown {
  const steps = key.split('.')
  return (row: T) => {
    let value: unknown = row
    for (const step of steps) {
      if (value === null || value === undefined) return undefined
      value = (value as Record<string, unknown>)[step]
    }
    return value
  }
}
