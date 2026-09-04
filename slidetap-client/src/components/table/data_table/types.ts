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

import type { ReactNode } from 'react'
import type {
  ColumnFiltersState,
  PaginationState,
  Row,
  RowData,
  SortingState,
} from '@tanstack/react-table'
import type { TableFeatures } from './features'

// The state a caller hands in and gets back is TanStack's own, so nothing
// outside this directory has to import a table component library to describe a
// filter or a page.
export type { ColumnFiltersState, PaginationState, RowData, SortingState }

/** One choice in a select or multi-select filter. */
export interface FilterOption {
  label: string
  value: string
}

/**
 * How a column is filtered.
 *
 * A union rather than a variant name beside a bag of options: a select filter
 * without anything to select is not a state to guard against at render time,
 * it is one that cannot be written down.
 */
export type FilterSpec =
  | { variant: 'text'; hint?: string }
  | { variant: 'select'; options: FilterOption[] }
  | { variant: 'multi-select'; options: FilterOption[] }
  | { variant: 'range' }
  | { variant: 'date-range' }

/**
 * Where the table is between asking for rows and having them.
 *
 * One value rather than a set of flags. While it is `loading` the table stands
 * in blank rows to fill the page, and those rows are shaped by the columns
 * rather than by the caller's data: drawing anything but a skeleton over them
 * would render nonsense. Keeping both off one value is what stops the two from
 * disagreeing.
 */
export type LoadState =
  | { status: 'loading' }
  | { status: 'ready' }
  | { status: 'refreshing' }
  | { status: 'error'; message: string }

/** The row handed to a cell renderer, so callers never name a TanStack type. */
export type TableRow<T extends RowData> = Row<TableFeatures, T>

export interface CellContext<T extends RowData> {
  row: T
  value: unknown
}

export interface ColumnDef<T extends RowData> {
  id: string
  header: string
  /** Reads the value by key, dotted for a nested one ("attributes.stain"). */
  accessorKey?: string
  /** Reads the value by hand, where a key cannot say it. */
  accessorFn?: (row: T) => unknown
  size?: number
  minSize?: number
  /**
   * Take a share of the width left over once every fixed column has its own.
   * Columns without it keep exactly their size, so a column sits at the same
   * offset in every table that shows it.
   */
  grow?: boolean
  Cell?: (context: CellContext<T>) => ReactNode
  filter?: FilterSpec
  sortable?: boolean
  /** Extra entries in the column's own menu, below the sorting ones. */
  headerMenu?: (close: () => void) => ReactNode[]
}

/**
 * Present when the rows on screen are one page of a larger set the server is
 * filtering, sorting and counting. Absent when the table holds everything it
 * shows and can do that work itself.
 */
export interface ServerSide {
  /** How many rows match, across every page. */
  rowCount: number
  filters: ColumnFiltersState
  sorting: SortingState
  pagination: PaginationState
  onFiltersChange: (filters: ColumnFiltersState) => void
  onSortingChange: (sorting: SortingState) => void
  onPaginationChange: (pagination: PaginationState) => void
}

export interface SelectionOptions {
  onChange?: (rowIds: string[]) => void
}

export interface DataTableOptions<T extends RowData> {
  columns: Array<ColumnDef<T>>
  data: T[]
  getRowId: (row: T) => string
  load: LoadState
  server?: ServerSide
  selection?: SelectionOptions
  /** Rendered in the last column of each row. */
  rowActions?: (row: T) => ReactNode
  /** Rendered above the table, to the left of the filter controls. */
  toolbar?: (context: ToolbarContext<T>) => ReactNode
  density?: 'compact' | 'comfortable'
  /** Sorted by this column when the caller has no sorting of its own. */
  defaultSort?: { id: string; descending: boolean }
}

/** What a toolbar is given: enough to act on the selection and to say what is shown. */
export interface ToolbarContext<T extends RowData> {
  /** The rows the reader is looking at, filtered and sorted. */
  rows: T[]
  selectedRowIds: string[]
  selectedRows: T[]
  clearSelection: () => void
}
