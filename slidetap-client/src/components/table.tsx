import {
  Add,
  Delete,
  Done,
  Edit,
  PriorityHigh,
  Recycling,
  RestoreFromTrash,
  WarningTwoTone,
} from '@mui/icons-material'
import { Box, IconButton, MenuItem, Tooltip, lighten } from '@mui/material'
import {
  MRT_GlobalFilterTextField,
  MRT_ToggleFiltersButton,
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
  type MRT_ColumnFiltersState,
  type MRT_PaginationState,
  type MRT_SortingState,
} from 'material-react-table'
import { Action, ActionStrings } from 'models/action'
import type { ItemSchema } from 'models/schema'
import type { ColumnFilter, ColumnSort, Item, TableItem } from 'models/table_item'
import React, { useEffect, useState } from 'react'

interface AttributeTableProps {
  getItems: (
    schema: ItemSchema,
    start: number,
    size: number,
    filters: ColumnFilter[],
    sorting: ColumnSort[],
    recycled?: boolean,
    invalid?: boolean,
  ) => Promise<{ items: Item[]; count: number }>
  schema: ItemSchema
  rowsSelectable?: boolean
  onRowAction?: (itemUid: string, action: Action) => void
  onRowsStateChange?: (itemUids: string[], state: boolean) => void
  onRowsEdit?: (itemUids: string[]) => void
  onNew?: () => void
}

interface TableProps {
  columns: Array<MRT_ColumnDef<any>>
  data: TableItem[]
  rowsSelectable?: boolean
  isLoading?: boolean
  onRowAction?: (itemUid: string, action: Action) => void
}

export function AttributeTable({
  getItems,
  schema,
  rowsSelectable,
  onRowAction,
  onRowsStateChange,
  onRowsEdit,
  onNew,
}: AttributeTableProps): React.ReactElement {
  const [data, setData] = useState<Item[]>([])
  const [rowCount, setRowCount] = useState(0)
  const [isError, setIsError] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [isRefetching, setIsRefetching] = useState(false)
  const [columnFilters, setColumnFilters] = useState<MRT_ColumnFiltersState>([])
  const [sorting, setSorting] = useState<MRT_SortingState>([])
  const [pagination, setPagination] = useState<MRT_PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  })
  const [displayRecycled, setDisplayRecycled] = useState(false)
  const [displayOnlyInValid, setDisplayOnlyInValid] = useState(false)
  useEffect(() => {
    const fetchData = (): void => {
      if (data.length === 0) {
        setIsLoading(true)
      } else {
        setIsRefetching(true)
      }
      getItems(
        schema,
        pagination.pageIndex * pagination.pageSize,
        pagination.pageSize,
        columnFilters,
        sorting.map((sort) => {
          if (sort.id === 'id') {
            return { column: 'identifier', isAttribute: false, descending: sort.desc }
          }
          if (sort.id === 'valid') {
            return { column: 'valid', isAttribute: false, descending: sort.desc }
          }
          return {
            column: sort.id.split('attributes.')[1],
            isAttribute: true,
            descending: sort.desc,
          }
        }),
        displayRecycled,
        displayOnlyInValid ? false : undefined,
      )
        .then(({ items, count }) => {
          setData(items)
          setRowCount(count)
          setIsError(false)
        })
        .catch((x) => {
          setIsError(true)
          console.error('failed to get items', x)
        })
      setIsLoading(false)
      setIsRefetching(false)
    }
    fetchData()
  }, [
    columnFilters,
    pagination.pageIndex,
    pagination.pageSize,
    sorting,
    getItems,
    data.length,
    displayOnlyInValid,
    displayRecycled,
    schema,
  ])
  const actions = [
    Action.VIEW,
    Action.EDIT,
    displayRecycled ? Action.RESTORE : Action.DELETE,
    Action.COPY,
  ]

  const handleRowsState = (): void => {
    if (displayRecycled === undefined) {
      return
    }
    onRowsStateChange?.(
      table.getSelectedRowModel().flatRows.map((row) => row.id),
      displayRecycled,
    )
  }

  const handleNew = (): void => {
    onNew?.()
  }

  const handleEdit = (): void => {
    onRowsEdit?.(table.getSelectedRowModel().flatRows.map((row) => row.id))
  }
  const columns = [
    { id: 'id', header: 'Id', accessorKey: 'identifier' },
    {
      id: 'valid',
      header: 'Valid',
      accessorKey: 'valid',
      Cell: ({ cell }) =>
        cell.getValue<boolean>() ? (
          <Done color="success" />
        ) : (
          <PriorityHigh color="warning" />
        ),
    },
    ...schema.attributes
      .filter((attributeSchema) => attributeSchema.displayInTable)
      .map((attributeSchema) => {
        return {
          header: attributeSchema.displayName,
          accessorKey: `attributes.${attributeSchema.tag}.displayValue`,
          id: `attributes.${attributeSchema.tag}`,
        }
      }),
  ]
  const table = useMaterialReactTable({
    columns,
    data,
    state: {
      isLoading,
      showAlertBanner: isError,
      showProgressBars: isRefetching,
      sorting,
      columnFilters,
      pagination,
    },
    initialState: { density: 'compact' },
    manualFiltering: true,
    manualPagination: true,
    manualSorting: true,
    onColumnFiltersChange: setColumnFilters,
    onPaginationChange: setPagination,
    onSortingChange: setSorting,
    rowCount,
    enableRowSelection: rowsSelectable,
    enableRowActions: true,
    positionActionsColumn: 'first',
    renderRowActionMenuItems: ({ row }) =>
      actions.map((action) => (
        <MenuItem
          key={action}
          onClick={() => {
            if (onRowAction === undefined) {
              return
            }
            const rowData = data[row.index]
            onRowAction(rowData.uid, action)
          }}
        >
          {ActionStrings[action]}
        </MenuItem>
      )),
    muiTableBodyRowProps: ({ row, table }) => ({
      onClick: (event) => {
        if (onRowAction !== undefined) {
          const rowData = data[row.index]
          onRowAction(rowData.uid, Action.VIEW)
        }
      },
    }),
    getRowId: (originalRow) => originalRow.uid,
    muiToolbarAlertBannerProps: isError
      ? {
          color: 'error',
          children: 'Error loading data',
        }
      : undefined,
    renderTopToolbar: ({ table }) => {
      return (
        <Box
          sx={(theme) => ({
            backgroundColor: lighten(theme.palette.background.default, 0.05),
            display: 'flex',
            gap: '0.5rem',
            p: '8px',
            justifyContent: 'space-between',
          })}
        >
          <Box>
            <Tooltip title="Toggle display of deleted items">
              <IconButton
                onClick={() => {
                  setDisplayOnlyInValid(false)
                  setDisplayRecycled(!displayRecycled)
                }}
                color={displayRecycled ? 'primary' : 'default'}
              >
                <Recycling />
              </IconButton>
            </Tooltip>
            <Tooltip title="Toggle display of invalid items">
              <IconButton
                onClick={() => {
                  setDisplayRecycled(false)
                  setDisplayOnlyInValid(!displayOnlyInValid)
                }}
                color={displayOnlyInValid ? 'primary' : 'default'}
              >
                <WarningTwoTone />
              </IconButton>
            </Tooltip>
          </Box>
          <Box sx={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <MRT_GlobalFilterTextField table={table} />
            <MRT_ToggleFiltersButton table={table} />
          </Box>
          <Box sx={{ display: 'flex', gap: '0.5rem' }}>
            {displayRecycled !== undefined && handleRowsState !== undefined && (
              <IconButton
                disabled={
                  !table.getIsSomeRowsSelected() && !table.getIsAllRowsSelected()
                }
                onClick={handleRowsState}
                color={
                  !table.getIsSomeRowsSelected() && !table.getIsAllRowsSelected()
                    ? 'default'
                    : 'primary'
                }
              >
                {displayRecycled ? <RestoreFromTrash /> : <Delete />}
              </IconButton>
            )}
            {onRowsEdit !== undefined && (
              <IconButton
                disabled={
                  !displayRecycled &&
                  !table.getIsSomeRowsSelected() &&
                  !table.getIsAllRowsSelected()
                }
                onClick={handleEdit}
                color={
                  !displayRecycled &&
                  !table.getIsSomeRowsSelected() &&
                  !table.getIsAllRowsSelected()
                    ? 'default'
                    : 'primary'
                }
              >
                <Edit />
              </IconButton>
            )}
            {onNew !== undefined && (
              <IconButton
                disabled={
                  !displayRecycled &&
                  (table.getIsSomeRowsSelected() || table.getIsAllRowsSelected())
                }
                onClick={handleNew}
                color={
                  !displayRecycled &&
                  (table.getIsSomeRowsSelected() || table.getIsAllRowsSelected())
                    ? 'default'
                    : 'primary'
                }
              >
                <Add />
              </IconButton>
            )}
          </Box>
        </Box>
      )
    },
  })
  return <MaterialReactTable table={table} />
}

export function Table({
  columns,
  data,
  rowsSelectable,
  isLoading,
  onRowAction,
}: TableProps): React.ReactElement {
  const actions = [Action.VIEW, Action.EDIT]
  const table = useMaterialReactTable({
    columns,
    data,
    state: { isLoading },
    enableRowSelection: rowsSelectable,
    enableGlobalFilter: false,
    enableRowActions: true,
    positionActionsColumn: 'last',
    renderRowActionMenuItems: ({ row }) =>
      actions.map((action) => (
        <MenuItem
          key={action}
          onClick={() => {
            if (onRowAction === undefined) {
              return
            }
            const rowData = data[row.index]
            onRowAction(rowData.uid, action)
          }}
        >
          {ActionStrings[action]}
        </MenuItem>
      )),
    muiTableBodyRowProps: ({ row, table }) => ({
      onClick: (event) => {
        if (onRowAction !== undefined) {
          const rowData = data[row.index]
          onRowAction(rowData.uid, Action.VIEW)
        }
      },
    }),
  })
  return <MaterialReactTable table={table} />
}
