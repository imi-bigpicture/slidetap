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

import { useState, type ReactElement } from 'react'
import { FilterList, MoreVert } from '@mui/icons-material'
import {
  Box,
  Divider,
  IconButton,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Tooltip,
  TableCell,
  TableSortLabel,
} from '@mui/material'
import type { ColumnDef, RowData } from '../types'

interface HeadCellProps<T extends RowData> {
  column: ColumnDef<T>
  sortDirection: 'asc' | 'desc' | false
  /** Cycles ascending, descending, unsorted. */
  onToggleSort: () => void
  /** Sorts one way, whatever the column is sorted by now. */
  onSort: (descending: boolean) => void
  onClearSort: () => void
  filter: ReactElement | null
  showFilters: boolean
  /** Show the filter row and put the cursor in this column's box. */
  onFilterByColumn: () => void
  /** Something is being filtered on in this column right now. */
  filterActive: boolean
  width: string
}

/**
 * A column heading: its name, whether the table is sorted by it, its own menu,
 * and the filter control when filters are shown.
 */
export function HeadCell<T extends RowData>({
  column,
  sortDirection,
  onToggleSort,
  onSort,
  onClearSort,
  filter,
  showFilters,
  onFilterByColumn,
  filterActive,
  width,
}: HeadCellProps<T>): ReactElement {
  const [menuAnchor, setMenuAnchor] = useState<HTMLElement | null>(null)
  const sortable = column.sortable ?? true
  const closeMenu = (): void => setMenuAnchor(null)

  const extraItems = column.headerMenu?.(closeMenu) ?? []
  const filterable = column.filter !== undefined
  const hasMenu = sortable || filterable || extraItems.length > 0

  return (
    <TableCell
      sx={{
        width,
        verticalAlign: 'top',
        px: 1,
        py: 0.75,
        fontWeight: 600,
      }}
      sortDirection={sortDirection}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.25, minHeight: 32 }}>
        {sortable ? (
          <TableSortLabel
            active={sortDirection !== false}
            direction={sortDirection === false ? 'asc' : sortDirection}
            onClick={onToggleSort}
          >
            {column.header}
          </TableSortLabel>
        ) : (
          <Box component="span">{column.header}</Box>
        )}
        <Box sx={{ flex: 1 }} />
        {filterActive && !showFilters && (
          <Tooltip title={`Filtered by ${column.header}`}>
            <IconButton
              size="small"
              color="primary"
              aria-label={`Filtered by ${column.header}, edit the filter`}
              onClick={onFilterByColumn}
            >
              <FilterList fontSize="inherit" />
            </IconButton>
          </Tooltip>
        )}
        {hasMenu && (
          <IconButton
            size="small"
            aria-label={`${column.header} column options`}
            onClick={(event) => setMenuAnchor(event.currentTarget)}
            sx={{ opacity: 0.5, '&:hover': { opacity: 1 } }}
          >
            <MoreVert fontSize="inherit" />
          </IconButton>
        )}
      </Box>
      {showFilters && filter !== null && <Box sx={{ pt: 0.5 }}>{filter}</Box>}
      <Menu anchorEl={menuAnchor} open={menuAnchor !== null} onClose={closeMenu}>
        {sortable && [
          <MenuItem
            key="asc"
            selected={sortDirection === 'asc'}
            onClick={() => {
              onSort(false)
              closeMenu()
            }}
          >
            Sort ascending
          </MenuItem>,
          <MenuItem
            key="desc"
            selected={sortDirection === 'desc'}
            onClick={() => {
              onSort(true)
              closeMenu()
            }}
          >
            Sort descending
          </MenuItem>,
          <MenuItem
            key="clear"
            disabled={sortDirection === false}
            onClick={() => {
              onClearSort()
              closeMenu()
            }}
          >
            Clear sort
          </MenuItem>,
        ]}
        {sortable && filterable && <Divider key="filter-divider" />}
        {/* The way into filtering one column, from the column itself. The
            toolbar's toggle shows every filter box at once, which is not what
            someone who has just decided to narrow this column is looking
            for. */}
        {filterable && (
          <MenuItem
            key="filter"
            onClick={() => {
              onFilterByColumn()
              closeMenu()
            }}
          >
            <ListItemIcon>
              <FilterList fontSize="small" />
            </ListItemIcon>
            <ListItemText>Filter by {column.header}</ListItemText>
          </MenuItem>
        )}
        {(sortable || filterable) && extraItems.length > 0 && <Divider key="divider" />}
        {extraItems}
      </Menu>
    </TableCell>
  )
}
