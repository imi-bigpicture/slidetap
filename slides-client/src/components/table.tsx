import React, { ReactElement, useEffect, useState } from 'react'
import MaterialReactTable, { MRT_RowSelectionState } from 'material-react-table'
import type { MRT_ColumnDef } from 'material-react-table'
import { ItemTableItem, TableItem } from 'models/table_item'

interface AttributeTableProps {
    columns: Array<MRT_ColumnDef<Object>>
    data: ItemTableItem[]
    rowsSelectable?: boolean
    isLoading?: boolean
    onCellClick?: (item: ItemTableItem, cellIdZ: string) => void
}

interface TableProps {
    columns: Array<MRT_ColumnDef<Object>>
    data: TableItem[]
    rowsSelectable?: boolean
    isLoading?: boolean
    onRowClick?: (item: TableItem) => void
}

export function AttributeTable (
    { columns, data, rowsSelectable, isLoading, onCellClick }: AttributeTableProps
): ReactElement {
    const [rowSelection, setRowSelection] = useState<MRT_RowSelectionState>({})
    useEffect(() => {
        const selected = Object.fromEntries(
            data.map((row, index) => [index, row.selected])
        )
        setRowSelection(selected)
    }, [data])

    return (
        <MaterialReactTable
            columns={columns}
            data={data}
            state={{ isLoading, rowSelection }}
            enableRowSelection={rowsSelectable}
            enableGlobalFilter={false}
            muiTableBodyCellProps={
                ({ cell, column, row, table }) => ({
                    onClick: (event) => {
                        if (onCellClick !== undefined) {
                            const rowData = data[row.index]
                            onCellClick(rowData, column.id)
                        }
                    }
                })
            }
            onRowSelectionChange={setRowSelection}
        />
    )
}

export function Table (
    { columns, data, rowsSelectable, isLoading, onRowClick }: TableProps
): ReactElement {
    return (
        <MaterialReactTable
            columns={columns}
            data={data}
            state={{ isLoading }}
            enableRowSelection={rowsSelectable}
            enableGlobalFilter={false}
            muiTableBodyRowProps={({ isDetailPanel, row, table }) => ({
                onClick: (event) => {
                    if (onRowClick !== undefined) {
                        const rowData = data[row.index]
                        onRowClick(rowData)
                    }
                }
            })}
        />
    )
}
