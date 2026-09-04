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
import { TablePagination } from '@mui/material'
import type { PaginationState } from '../types'

const PAGE_SIZES = [5, 10, 25, 50, 100]

interface PaginationBarProps {
  pagination: PaginationState
  rowCount: number
  onChange: (pagination: PaginationState) => void
  /** The count is not known yet, so the range is written without a total. */
  pending: boolean
}

export function PaginationBar({
  pagination,
  rowCount,
  onChange,
  pending,
}: PaginationBarProps): ReactElement {
  return (
    <TablePagination
      component="div"
      count={pending ? -1 : rowCount}
      page={pagination.pageIndex}
      rowsPerPage={pagination.pageSize}
      rowsPerPageOptions={PAGE_SIZES}
      onPageChange={(_, page) => onChange({ ...pagination, pageIndex: page })}
      onRowsPerPageChange={(event) =>
        // Back to the first page: a page is a position in one list, and a
        // longer page has no fourth one to land on.
        onChange({ pageIndex: 0, pageSize: Number(event.target.value) })
      }
      showFirstButton
      showLastButton
    />
  )
}
