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

import { Stack } from '@mui/material'
import Button from '@mui/material/Button'
import Grid from '@mui/material/Grid2'
import { useQueryClient } from '@tanstack/react-query'
import React from 'react'
import StatusChip from 'src/components/status_chip'
import { ImageTable } from 'src/components/table/image_table'
import { Action } from 'src/models/action'
import { Batch } from 'src/models/batch'
import { BatchStatus } from 'src/models/batch_status'
import {
  ImageStatus,
  ImageStatusList,
  ImageStatusStrings,
} from 'src/models/image_status'
import { Image } from 'src/models/item'
import type { Project } from 'src/models/project'
import type { ColumnFilter, ColumnSort } from 'src/models/table_item'
import batchApi from 'src/services/api/batch.api'
import itemApi from 'src/services/api/item_api'
import { useSchemaContext } from '../../../contexts/schema/schema_context'

interface PreProcessImagesProps {
  project: Project
  batch: Batch
}

function PreProcessImages({
  project,
  batch,
}: PreProcessImagesProps): React.ReactElement {
  return (
    <Grid container spacing={1} justifyContent="flex-start" alignItems="flex-start">
      {/* <Grid size={{ xs: 12 }}>
        <StepHeader
          title="Pre-process"
          description={
            batch.status === BatchStatus.METADATA_SEARCH_COMPLETE
              ? 'Pre-process images in batch.'
              : 'Status of image pre-processing.'
          }
        />
      </Grid> */}
      {batch.status === BatchStatus.METADATA_SEARCH_COMPLETE ? (
        <StartPreProcessImages batch={batch} />
      ) : (
        <PreprocessImagesProgress project={project} batch={batch} />
      )}
    </Grid>
  )
}

export default PreProcessImages

interface StartPreProcessImagesProps {
  batch: Batch
}

function StartPreProcessImages({
  batch,
}: StartPreProcessImagesProps): React.ReactElement {
  const queryClient = useQueryClient()
  const [starting, setStarting] = React.useState(false)
  const handleStartPreProcessingImages = (): void => {
    setStarting(true)
    batchApi
      .preProcess(batch.uid)
      .then((updatedBatch) => {
        queryClient.setQueryData(['batch', batch.uid], updatedBatch)
      })
      .catch((x) => {
        console.error('Failed to download project', x)
      })
  }

  // TODO add count of items in project
  return (
    <Grid size={{ xs: 4 }}>
      <Stack spacing={1}>
        {/* {Object.values(rootSchemaQuery.data.samples).map((itemSchema, index) => (
          <TextField
            key={index}
            label={itemSchema.name}
            value={itemSchema.count}
            InputProps={{ readOnly: true }}
          />
        ))} */}
        <Button disabled={starting} onClick={handleStartPreProcessingImages}>
          Pre-process
        </Button>
      </Stack>
    </Grid>
  )
}

interface PreprocessImagesProgressProps {
  project: Project
  batch: Batch
}

function PreprocessImagesProgress({
  project,
  batch,
}: PreprocessImagesProgressProps): React.ReactElement {
  const rootSchema = useSchemaContext()

  const getImages = async (
    start: number,
    size: number,
    filters: ColumnFilter[],
    sorting: ColumnSort[],
  ): Promise<{ items: Image[]; count: number }> => {
    const statusFilter = filters.find((filter) => filter.id === 'status')?.value
      ? (filters.find((filter) => filter.id === 'status')?.value as string[]).map(
          (status) => parseInt(status),
        )
      : undefined
    const request = {
      start,
      size,
      identifierFilter: filters.find((filter) => filter.id === 'id')?.value as string,
      attributeFilters:
        filters.length > 0
          ? filters
              .filter((filter) => filter.id.startsWith('attributes.'))
              .reduce<Record<string, string>>(
                (attributeFilters, filter) => ({
                  ...attributeFilters,
                  [filter.id.split('attributes.')[1]]: String(filter.value),
                }),
                {},
              )
          : undefined,
      sorting: sorting.length > 0 ? sorting : undefined,
      statusFilter: statusFilter,
    }
    return await itemApi
      .getItems<Image>(
        Object.values(rootSchema.images)[0].uid,
        project.datasetUid,
        batch.uid,
        request,
      )
      .then(({ items, count }) => {
        return {
          items: items,
          count,
        }
      })
  }
  // const handleDeleteOrRestoreAction = (image: Image): void => {
  //   itemApi.select(image.uid, image.status !== ImageStatus.NOT_STARTED).catch((x) => {
  //     console.error('Failed to select image', x)
  //   })
  // }
  const handleRetryAction = (image: Image): void => {
    itemApi.retry([image.uid]).catch((x) => {
      console.error('Failed to retry image', x)
    })
  }

  const handleRetryEnabled = (image: Image): boolean => {
    return (
      image.status === ImageStatus.DOWNLOADING_FAILED ||
      image.status === ImageStatus.PRE_PROCESSING_FAILED ||
      image.status === ImageStatus.POST_PROCESSING_FAILED
    )
  }
  const handleImagesRetry = (imageUids: string[]): void => {
    itemApi.retry(imageUids).catch((x) => {
      console.error('Failed to retry images', x)
    })
  }
  return (
    <Grid size={{ xs: 12 }}>
      <ImageTable
        getItems={getImages}
        columns={[
          {
            header: 'Identifier',
            accessorKey: 'identifier',
          },
          {
            header: 'Status',
            accessorKey: 'status',
            Cell: ({ row }) => (
              <StatusChip
                status={row.original.status}
                stringMap={ImageStatusStrings}
                colorMap={{
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
                }}
              />
            ),
            filterVariant: 'multi-select',
            filterSelectOptions: ImageStatusList.map((status) => ({
              label: ImageStatusStrings[status],
              value: status.toString(),
            })),
          },
          {
            header: 'Message',
            accessorKey: 'statusMessage',
          },
        ]}
        rowsSelectable={true}
        actions={[
          // {
          //   action: Action.DELETE,
          //   onAction: handleDeleteOrRestoreAction,
          // },
          // {
          //   action: Action.RESTORE,
          //   onAction: handleDeleteOrRestoreAction,
          // },
          {
            action: Action.RETRY,
            onAction: handleRetryAction,
            enabled: handleRetryEnabled,
          },
        ]}
        onRowsRetry={handleImagesRetry}
      />
    </Grid>
  )
}
