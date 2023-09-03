import React, { ReactElement, useEffect, useState } from 'react'
import MaterialReactTable, { MRT_RowSelectionState } from 'material-react-table'
import type { MRT_ColumnDef } from 'material-react-table'
import { ItemTableItem, TableItem } from 'models/table_item'

interface AttributeTableProps {
    columns: Array<MRT_ColumnDef<Object>>
    data: ItemTableItem[]
    rowsSelectable?: boolean
    isLoading?: boolean
    onCellClick?: (item: ItemTableItem, cellId: string) => void
    onRowSelect?: (itemUid: string, value: boolean) => void
}

interface TableProps {
    columns: Array<MRT_ColumnDef<Object>>
    data: TableItem[]
    rowsSelectable?: boolean
    isLoading?: boolean
    onRowClick?: (item: TableItem) => void
}

export function AttributeTable (
    {
        columns,
        data,
        rowsSelectable,
        isLoading,
        onCellClick,
        onRowSelect
    }: AttributeTableProps
): ReactElement {
    const [rowSelection, setRowSelection] = useState<MRT_RowSelectionState>({})
    //     Object.fromEntries(data.map(item => [item.uid, item.selected])
    // ))
    useEffect(() => {
        const selected = Object.fromEntries(
            data.map((item, index) => [index, item.selected])
        )
        console.log('set selected', selected)
        setRowSelection(selected)
    }, [data])
    useEffect(() => {
        if (onRowSelect === undefined) {
            return
        }
        data.forEach((item, index) => {
            const selected = rowSelection[index] !== undefined
            if (selected !== item.selected) {
                onRowSelect(item.uid, selected)
            }
        })
    }, [onRowSelect, rowSelection, data])
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
        // getRowId={(originalRow) => originalRow.uid}

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
