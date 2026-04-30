//    Copyright 2024 SECTRA AB
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

import { Block, Refresh } from '@mui/icons-material'
import { Box, Chip, IconButton, Tooltip } from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
    MaterialReactTable,
    useMaterialReactTable,
    type MRT_ColumnDef,
} from 'material-react-table'
import React, { type ReactElement } from 'react'
import {
    MetadataImportStatus,
    MetadataImportStatusColors,
    MetadataImportStatusStrings,
} from 'src/models/metadata_import_status'
import type { MetadataSearchItem } from 'src/models/metadata_search_item'
import metadataSearchApi from 'src/services/api/metadata_search_api'

interface MetadataSearchItemsTableProps {
    batchUid: string
}

const SEARCH_ITEMS_QUERY_KEY = (batchUid: string) =>
    ['metadataSearchItems', batchUid] as const

const SUPPORTS_RETRY_QUERY_KEY = ['metadataSearchSupportsRetry'] as const

function MetadataSearchItemsTable({
    batchUid,
}: MetadataSearchItemsTableProps): ReactElement {
    const queryClient = useQueryClient()

    const supportsRetryQuery = useQuery({
        queryKey: SUPPORTS_RETRY_QUERY_KEY,
        queryFn: () => metadataSearchApi.supportsRetry(),
    })
    const supportsRetry = supportsRetryQuery.data ?? false

    const itemsQuery = useQuery({
        queryKey: SEARCH_ITEMS_QUERY_KEY(batchUid),
        queryFn: () => metadataSearchApi.listForBatch(batchUid),
        refetchInterval: (query) => {
            const data = query.state.data as MetadataSearchItem[] | undefined
            const hasInflight = data?.some(
                (item) => item.status === MetadataImportStatus.NOT_STARTED,
            )
            return hasInflight ? 2000 : false
        },
    })

    const invalidate = (): void => {
        queryClient.invalidateQueries({
            queryKey: SEARCH_ITEMS_QUERY_KEY(batchUid),
        })
    }
    const retryMutation = useMutation({
        mutationFn: (uid: string) => metadataSearchApi.retry(uid),
        onSuccess: invalidate,
    })
    const excludeMutation = useMutation({
        mutationFn: (uid: string) => metadataSearchApi.exclude(uid),
        onSuccess: invalidate,
    })

    const columns: MRT_ColumnDef<MetadataSearchItem>[] = [
        {
            id: 'identifier',
            header: 'Identifier',
            accessorKey: 'identifier',
        },
        {
            id: 'status',
            header: 'Status',
            accessorKey: 'status',
            size: 100,
            Cell: ({ row }) => {
                const item = row.original
                const chip = (
                    <Chip
                        size="small"
                        label={MetadataImportStatusStrings[item.status]}
                        color={MetadataImportStatusColors[item.status]}
                    />
                )
                if (
                    item.status === MetadataImportStatus.FAILED &&
                    item.message != null
                ) {
                    return <Tooltip title={item.message}>{chip}</Tooltip>
                }
                return chip
            },
        },
        {
            id: 'message',
            header: 'Message',
            accessorKey: 'message',
        },
        {
            id: 'retryCount',
            header: 'Retries',
            accessorKey: 'retryCount',
            size: 80,
        },
        {
            id: 'attemptedAt',
            header: 'Attempted at',
            accessorKey: 'attemptedAt',
            Cell: ({ cell }) => {
                const value = cell.getValue<string | null>()
                return value ? new Date(value).toLocaleString() : ''
            },
        },
    ]

    const table = useMaterialReactTable({
        columns,
        data: itemsQuery.data ?? [],
        state: {
            isLoading: itemsQuery.isLoading,
            showProgressBars: itemsQuery.isFetching,
        },
        initialState: { density: 'compact' },
        enableRowActions: true,
        positionActionsColumn: 'last',
        renderRowActions: ({ row }) => {
            const item = row.original
            if (item.status !== MetadataImportStatus.FAILED) {
                return <Box />
            }
            const retryDisabled = !supportsRetry || retryMutation.isPending
            const retryTooltip = !supportsRetry
                ? 'This importer does not support per-item retry'
                : 'Retry metadata import for this item'
            return (
                <Box>
                    <Tooltip title={retryTooltip}>
                        <span>
                            <IconButton
                                size="small"
                                disabled={retryDisabled}
                                onClick={() => retryMutation.mutate(item.uid)}
                            >
                                <Refresh />
                            </IconButton>
                        </span>
                    </Tooltip>
                    <Tooltip title="Remove from this view">
                        <span>
                            <IconButton
                                size="small"
                                disabled={excludeMutation.isPending}
                                onClick={() => excludeMutation.mutate(item.uid)}
                            >
                                <Block />
                            </IconButton>
                        </span>
                    </Tooltip>
                </Box>
            )
        },
        getRowId: (row) => row.uid,
    })

    return <MaterialReactTable table={table} />
}

export default MetadataSearchItemsTable
