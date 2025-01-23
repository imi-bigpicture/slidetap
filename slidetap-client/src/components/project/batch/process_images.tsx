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

import { LinearProgress, Stack, Tooltip } from '@mui/material'
import Button from '@mui/material/Button'
import Grid from '@mui/material/Grid2'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import React, { type ReactElement } from 'react'
import StatusChip from 'src/components/status_chip'
import { ImageTable } from 'src/components/table/image_table'
import { ImageAction } from 'src/models/action'
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
import DisplayBatchValidation from './display_batch_validation'

interface ProcessImagesProps {
  project: Project
  batch: Batch
}

function ProcessImages({ project, batch }: ProcessImagesProps): ReactElement {
  return (
    <Grid container spacing={1} justifyContent="flex-start" alignItems="flex-start">
      {/* <Grid size={{ xs: 12 }}>
        <StepHeader
          title="Process"
          description={
            batch.status === BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE
              ? 'Process images in batch.'
              : 'Status of image processing.'
          }
        />
      </Grid> */}
      {batch.status === BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE ? (
        <StartProcessImages batch={batch} />
      ) : (
        <ProcessImagesProgress project={project} batch={batch} />
      )}
    </Grid>
  )
}

export default ProcessImages

interface StartProcessImagesProps {
  batch: Batch
}

function StartProcessImages({ batch }: StartProcessImagesProps): React.ReactElement {
  const queryClient = useQueryClient()
  const [starting, setStarting] = React.useState(false)
  const validationQuery = useQuery({
    queryKey: ['batchValidation', batch.uid],
    queryFn: async () => {
      return await batchApi.getValidation(batch.uid)
    },
  })

  const handleStartProject = (): void => {
    setStarting(true)
    batchApi
      .process(batch.uid)
      .then((updatedBatch) => {
        queryClient.setQueryData(['batch', batch.uid], updatedBatch)
      })
      .catch((x) => {
        console.error('Failed to start project', x)
      })
  }
  if (validationQuery.data === undefined) {
    return <LinearProgress />
  }
  const isNotValid = validationQuery.data === undefined || !validationQuery.data.valid
  return (
    <Grid size={{ xs: 4 }}>
      <Stack spacing={1}>
        <Tooltip
          title={
            isNotValid ? 'Project contains items that are not yet valid' : undefined
          }
        >
          <Stack>
            <Button disabled={isNotValid || starting} onClick={handleStartProject}>
              Start
            </Button>
          </Stack>
        </Tooltip>
      </Stack>
      {isNotValid &&
        validationQuery.data !== undefined &&
        DisplayBatchValidation({ validation: validationQuery.data })}
    </Grid>
  )
}

interface ProcessImagesProgressProps {
  project: Project
  batch: Batch
}

function ProcessImagesProgress({
  project,
  batch,
}: ProcessImagesProgressProps): React.ReactElement {
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
  const handleImageAction = (imageUid: string, action: ImageAction): void => {
    if (action === ImageAction.DELETE || action === ImageAction.RESTORE) {
      itemApi.select(imageUid, action === ImageAction.RESTORE).catch((x) => {
        console.error('Failed to select image', x)
      })
    } else if (action === ImageAction.RETRY) {
      itemApi.retry([imageUid]).catch((x) => {
        console.error('Failed to retry image', x)
      })
    }
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
            id: 'id',
            header: 'Identifier',
            accessorKey: 'identifier',
          },
          {
            id: 'status',
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
            id: 'status',
            header: 'Message',
            accessorKey: 'statusMessage',
          },
        ]}
        rowsSelectable={true}
        onRowAction={handleImageAction}
        onRowsRetry={handleImagesRetry}
      />
    </Grid>
  )
}
