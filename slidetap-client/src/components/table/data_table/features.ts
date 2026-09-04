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
  columnFilteringFeature,
  columnSizingFeature,
  columnVisibilityFeature,
  createCoreRowModel,
  createFilteredRowModel,
  createPaginatedRowModel,
  createSortedRowModel,
  filterFns,
  rowPaginationFeature,
  rowSelectionFeature,
  rowSortingFeature,
  sortFns,
  tableFeatures,
} from '@tanstack/react-table'

/**
 * Everything the tables here do, and nothing else.
 *
 * Named one by one rather than taken from `stockFeatures`, because a feature
 * registered here does work on every render whether or not anything asks for
 * it. Faceting is the clearest case: registering it computes the distinct
 * values of every column on every pass, to fill dropdowns these tables build
 * from their own data instead.
 *
 * Row models are gated at runtime by the `manual*` options, so a server-side
 * table runs the filtered/sorted/paginated models over rows it has already
 * been given in order, which costs a pass over one page.
 */
export const tableFeatureBundle = tableFeatures({
  columnFilteringFeature,
  columnSizingFeature,
  columnVisibilityFeature,
  rowPaginationFeature,
  rowSelectionFeature,
  rowSortingFeature,
  coreRowModel: createCoreRowModel(),
  filteredRowModel: createFilteredRowModel(),
  sortedRowModel: createSortedRowModel(),
  paginatedRowModel: createPaginatedRowModel(),
  filterFns,
  sortFns,
})

export type TableFeatures = typeof tableFeatureBundle
