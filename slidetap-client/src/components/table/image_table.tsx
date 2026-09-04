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
import { Box, IconButton } from '@mui/material'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import {
  DataTableView,
  useDataTable,
  type ColumnDef,
  type ColumnFiltersState,
  type PaginationState,
  type SortingState,
} from './data_table'
import React, { useMemo, useState } from 'react'
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
import { queryKeys } from 'src/services/query_keys'
import StatusChip from '../status_chip'
import { getItems } from './get_table_items'
import RowActions from './row_actions'
import { CopyValueButton } from './table_interaction'

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
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [sorting, setSorting] = useState<SortingState>([])
  const [pagination, setPagination] = useState<PaginationState>({
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
        isImageItem(item) ? (item.samples?.[schema.sampleUid]?.length ?? 0) : 0,
    }
  })
  imageSchema.annotations.forEach((schema) => {
    relationships[`relation.${schema.uid}.annotation.${schema.annotationUid}`] = {
      title: schema.annotationTitle,
      relationSchemaUid: schema.annotationUid,
      relationType: RelationFilterType.ANNOTATION,
      valueGetter: (item: Item) =>
        isImageItem(item) ? (item.annotations?.[schema.annotationUid]?.length ?? 0) : 0,
    }
  })
  imageSchema.observations.forEach((schema) => {
    relationships[`relation.${schema.uid}.observation.${schema.observationUid}`] = {
      title: schema.observationTitle,
      relationSchemaUid: schema.observationUid,
      relationType: RelationFilterType.OBSERVATION,
      valueGetter: (item: Item) =>
        isImageItem(item)
          ? (item.observations?.[schema.observationUid]?.length ?? 0)
          : 0,
    }
  })
  const statusColorMap: Record<
    ImageStatus,
    'success' | 'error' | 'primary' | 'secondary' | 'warning'
  > = {
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
    [ImageStatus.STORING]: 'primary',
    [ImageStatus.STORING_FAILED]: 'error',
    [ImageStatus.STORED]: 'success',
  }

  // Built once per set of inputs. A fresh array on every render makes
  // TanStack discard every column object and the caches on it.
  // statusColorMap is rebuilt with it and holds only constants.
  const columns = useMemo<Array<ColumnDef<Image>>>(
    () => [
      {
        id: 'id',
        header: pseudonymMode ? 'Pseudonym' : 'Identifier',
        accessorKey: 'identifier',
        Cell: ({ row }) => {
          const identifier = getDisplayIdentifier(row, pseudonymMode)
          return (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              {/* Monospace like the other identifiers, but images have no detail
                  view to open, so it is not a link. */}
              <Box component="span" sx={{ fontFamily: 'monospace', fontWeight: 500 }}>
                {identifier}
              </Box>
              <CopyValueButton value={identifier} label="Copy identifier" />
            </Box>
          )
        },
        filter: { variant: 'text' },
      },
      {
        id: 'status',
        header: 'Status',
        accessorKey: 'status',
        Cell: ({ row }) => {
          const image = row
          return (
            <StatusChip
              status={image.status}
              stringMap={ImageStatusStrings}
              colorMap={statusColorMap}
            />
          )
        },
        filter: {
          variant: 'multi-select',
          options: ImageStatusList.map((status) => ({
            label: ImageStatusStrings[status],
            value: status.toString(),
          })),
        },
      },
      {
        id: 'message',
        header: 'Message',
        accessorKey: 'statusMessage',
        // The request builder has no sort for it, and rejects the query for
        // any column it does not know.
        sortable: false,
      },
      {
        id: 'lastHeartbeatAt',
        header: 'Last heartbeat',
        accessorKey: 'lastHeartbeatAt',
        sortable: false,
        Cell: ({ value }) => {
          const at = value as string | null
          if (at == null) {
            return ''
          }
          const date = new Date(at)
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
    ],
    [pseudonymMode],
  )
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
        {},
        undefined,
        undefined,
        pseudonymMode,
      )
    },
    refetchInterval: refresh ? 2000 : false,
    placeholderData: keepPreviousData,
  })
  const table = useDataTable<Image>({
    columns,
    data: imagesQuery.data?.items ?? [],
    getRowId: (image) => image.uid,
    // One value, so the skeletons the table draws and the blank rows it draws
    // them over can never be asked for separately.
    load: imagesQuery.isError
      ? { status: 'error', message: 'Error loading data' }
      : imagesQuery.isLoading
        ? { status: 'loading' }
        : imagesQuery.isRefetching
          ? { status: 'refreshing' }
          : { status: 'ready' },
    density: 'compact',
    server: {
      rowCount: imagesQuery.data?.count ?? 0,
      filters: columnFilters,
      sorting,
      pagination,
      onFiltersChange: setColumnFilters,
      onSortingChange: setSorting,
      onPaginationChange: setPagination,
    },
    selection: {},
    rowActions: (image) => <RowActions item={image} actions={actions} />,
    toolbar: ({ selectedRowIds }) =>
      onRowsRetry !== undefined && (
        <IconButton
          disabled={selectedRowIds.length === 0}
          color={selectedRowIds.length === 0 ? 'default' : 'primary'}
          onClick={() => onRowsRetry(selectedRowIds)}
          aria-label={`Retry ${selectedRowIds.length} images`}
        >
          <Replay />
        </IconButton>
      ),
  })

  return <DataTableView table={table} />
}
