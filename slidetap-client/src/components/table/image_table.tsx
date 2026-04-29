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

import { Replay } from '@mui/icons-material'
import { Box, IconButton, lighten } from '@mui/material'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import {
  MRT_ColumnDef,
  MRT_GlobalFilterTextField,
  MRT_ToggleFiltersButton,
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnFiltersState,
  type MRT_PaginationState,
  type MRT_SortingState,
} from 'material-react-table'
import React, { useState } from 'react'
import { Action } from 'src/models/action'
import { Batch } from 'src/models/batch'
import { isImageItem } from 'src/models/helpers'
import {
  ImageStatus,
  ImageStatusList,
  ImageStatusStrings,
} from 'src/models/image_status'
import { Image, Item } from 'src/models/item'
import { Project } from 'src/models/project'
import { ImageSchema } from 'src/models/schema/item_schema'
import { getDisplayIdentifier } from 'src/models/pseudonym'
import { RelationFilterDefinition, RelationFilterType } from 'src/models/table_item'
import { usePseudonym } from 'src/contexts/pseudonym/pseudonym_context'
import configApi from 'src/services/api/config_api'
import { queryKeys } from 'src/services/query_keys'
import StatusChip from '../status_chip'
import { getItems } from './get_table_items'
import RowActions from './row_actions'

export function isImageStuck(image: Image, thresholdSeconds: number): boolean {
  if (
    image.status !== ImageStatus.PRE_PROCESSING &&
    image.status !== ImageStatus.POST_PROCESSING
  ) {
    return false
  }
  if (image.processingStartedAt == null) {
    return true
  }
  const elapsed =
    (Date.now() - new Date(image.processingStartedAt).getTime()) / 1000
  return elapsed > thresholdSeconds
}

interface ImageTableProps {
  project: Project
  batch: Batch
  imageSchema: ImageSchema
  actions?: {
    action: Action
    onAction: (item: Image) => void
    enabled?: (item: Image) => boolean
    inMenu?: boolean
  }[]
  onRowsRetry?: (itemUids: string[]) => void
  refresh: boolean
}

export function ImageTable({
  project,
  batch,
  imageSchema,
  actions,
  onRowsRetry,
  refresh,
}: ImageTableProps): React.ReactElement {
  const { pseudonymMode } = usePseudonym()
  const [columnFilters, setColumnFilters] = useState<MRT_ColumnFiltersState>([])
  const [sorting, setSorting] = useState<MRT_SortingState>([])
  const [pagination, setPagination] = useState<MRT_PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  })
  const relationships: Record<string, RelationFilterDefinition> = {}
  imageSchema.samples.forEach((schema) => {
    relationships[`relation.${schema.uid}.sample.${schema.sampleUid}`] = {
      title: schema.sampleTitle,
      relationSchemaUid: schema.sampleUid,
      relationType: RelationFilterType.SAMPLE,
      valueGetter: (item: Item) =>
        isImageItem(item) ? item.samples?.[schema.sampleUid]?.length ?? 0 : 0,
    }
  })
  imageSchema.annotations.forEach((schema) => {
    relationships[`relation.${schema.uid}.annotation.${schema.annotationUid}`] = {
      title: schema.annotationTitle,
      relationSchemaUid: schema.annotationUid,
      relationType: RelationFilterType.ANNOTATION,
      valueGetter: (item: Item) =>
        isImageItem(item) ? item.annotations?.[schema.annotationUid]?.length ?? 0 : 0,
    }
  })
  imageSchema.observations.forEach((schema) => {
    relationships[`relation.${schema.uid}.observation.${schema.observationUid}`] = {
      title: schema.observationTitle,
      relationSchemaUid: schema.observationUid,
      relationType: RelationFilterType.OBSERVATION,
      valueGetter: (item: Item) =>
        isImageItem(item) ? item.observations?.[schema.observationUid]?.length ?? 0 : 0,
    }
  })
  const configQuery = useQuery({
    queryKey: queryKeys.config.all,
    queryFn: configApi.getConfig,
    staleTime: Infinity,
  })
  const stuckThreshold = configQuery.data?.stuckProcessingThresholdSeconds ?? 3600

  const statusColorMap: Record<ImageStatus, 'success' | 'error' | 'primary' | 'secondary' | 'warning'> = {
    [ImageStatus.NOT_STARTED]: 'secondary',
    [ImageStatus.DOWNLOADING]: 'primary',
    [ImageStatus.DOWNLOADING_FAILED]: 'error',
    [ImageStatus.DOWNLOADED]: 'primary',
    [ImageStatus.PRE_PROCESSING]: 'primary',
    [ImageStatus.PRE_PROCESSING_FAILED]: 'error',
    [ImageStatus.PRE_PROCESSED]: 'success',
    [ImageStatus.POST_PROCESSING]: 'primary',
    [ImageStatus.POST_PROCESSING_FAILED]: 'error',
    [ImageStatus.POST_PROCESSED]: 'success',
  }

  const columns: MRT_ColumnDef<Image>[] = [
    {
      id: 'id',
      header: pseudonymMode ? 'Pseudonym' : 'Identifier',
      accessorKey: 'identifier',
      Cell: ({ row }) => getDisplayIdentifier(row.original, pseudonymMode),
      muiFilterTextFieldProps: {
        placeholder: pseudonymMode ? 'Pseudonym' : 'Identifier',
      },
    },
    {
      id: 'status',
      header: 'Status',
      accessorKey: 'status',
      Cell: ({ row }) => {
        const image = row.original
        const stuck = isImageStuck(image, stuckThreshold)
        const color = stuck ? 'warning' : statusColorMap[image.status]
        const label = stuck
          ? `${ImageStatusStrings[image.status]} (stuck?)`
          : ImageStatusStrings[image.status]
        return (
          <StatusChip
            status={image.status}
            stringMap={{ ...ImageStatusStrings, [image.status]: label }}
            colorMap={{ ...statusColorMap, [image.status]: color }}
          />
        )
      },
      filterVariant: 'multi-select',
      filterSelectOptions: ImageStatusList.map((status) => ({
        label: ImageStatusStrings[status],
        value: status.toString(),
      })),
    },
    {
      id: 'message',
      header: 'Message',
      accessorKey: 'statusMessage',
    },
    {
      id: 'lastHeartbeatAt',
      header: 'Last heartbeat',
      accessorKey: 'lastHeartbeatAt',
      enableColumnFilter: false,
      Cell: ({ cell }) => {
        const value = cell.getValue<string | null>()
        if (value == null) {
          return ''
        }
        const date = new Date(value)
        const elapsedSec = Math.max(
          0,
          Math.round((Date.now() - date.getTime()) / 1000),
        )
        const label =
          elapsedSec < 60
            ? `${elapsedSec}s ago`
            : elapsedSec < 3600
              ? `${Math.round(elapsedSec / 60)}m ago`
              : `${Math.round(elapsedSec / 3600)}h ago`
        return <span title={date.toLocaleString()}>{label}</span>
      },
    },
  ]
  const imagesQuery = useQuery({
    queryKey: [
      ...queryKeys.item.table(
        imageSchema.uid,
        project.datasetUid,
        batch?.uid,
        relationships,
        pagination.pageIndex * pagination.pageSize,
        pagination.pageSize,
        columnFilters,
        sorting,
      ),
      pseudonymMode,
    ],
    queryFn: async () => {
      return await getItems<Image>(
        imageSchema.uid,
        project.datasetUid,
        batch,
        relationships,
        pagination.pageIndex * pagination.pageSize,
        pagination.pageSize,
        columnFilters,
        sorting,
        undefined,
        undefined,
        pseudonymMode,
      )
    },
    refetchInterval: refresh ? 2000 : false,
    placeholderData: keepPreviousData,
  })
  const handleRetry = (): void => {
    onRowsRetry?.(table.getSelectedRowModel().flatRows.map((row) => row.id))
  }

  const table = useMaterialReactTable({
    columns,
    data: imagesQuery.data?.items ?? [],
    state: {
      isLoading: imagesQuery.isLoading,
      showAlertBanner: imagesQuery.isError,
      showProgressBars: imagesQuery.isRefetching,
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
    rowCount: imagesQuery.data?.count ?? 0,
    enableRowSelection: true,
    enableRowActions: true,
    positionActionsColumn: 'last',
    renderRowActions: ({ row }) => <RowActions row={row} actions={actions} />,
    getRowId: (originalRow) => originalRow.uid,
    muiToolbarAlertBannerProps: imagesQuery.isError
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
          <Box></Box>
          <Box sx={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <MRT_GlobalFilterTextField table={table} />
            <MRT_ToggleFiltersButton table={table} />
          </Box>
          <Box sx={{ display: 'flex', gap: '0.5rem' }}>
            {onRowsRetry !== undefined && (
              <IconButton
                disabled={
                  !table.getIsSomeRowsSelected() && !table.getIsAllRowsSelected()
                }
                onClick={handleRetry}
                color={
                  !table.getIsSomeRowsSelected() && !table.getIsAllRowsSelected()
                    ? 'default'
                    : 'primary'
                }
              >
                <Replay />
              </IconButton>
            )}
          </Box>
        </Box>
      )
    },
  })
  return <MaterialReactTable table={table} />
}
