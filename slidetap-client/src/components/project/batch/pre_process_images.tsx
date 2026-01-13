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
import Grid from '@mui/material/Grid'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import React from 'react'
import { ImageTable } from 'src/components/table/image_table'
import { useError } from 'src/contexts/error/error_context'
import { Action } from 'src/models/action'
import { Batch } from 'src/models/batch'
import { BatchStatus } from 'src/models/batch_status'
import { ImageStatus } from 'src/models/image_status'
import { Image } from 'src/models/item'
import type { Project } from 'src/models/project'
import batchApi from 'src/services/api/batch.api'
import itemApi from 'src/services/api/item_api'
import { queryKeys } from 'src/services/query_keys'
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

  const startProjectMutation = useMutation({
    mutationFn: (batchUid: string) => {
      return batchApi.preProcess(batchUid)
    },
    onSuccess: (updatedBatch) => {
      queryClient.setQueryData(queryKeys.batch.detail(batch.uid), updatedBatch)
    },
  })

  const handleStartPreProcessingImages = (): void => {
    setStarting(true)
    startProjectMutation.mutate(batch.uid)
  }

  // TODO add count of items in project
  return (
    <Grid size={{ xs: 4 }}>
      <Stack spacing={1}>
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
  const { showError } = useError()
  const imageSchema = Object.values(rootSchema.images)[0]

  const handleRetryAction = (image: Image): void => {
    itemApi.retry([image.uid]).catch((error) => {
      console.error('Failed to retry image', error)
      showError('Failed to retry image')
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
    itemApi.retry(imageUids).catch((error) => {
      console.error('Failed to retry images', error)
      showError('Failed to retry images')
    })
  }
  return (
    <Grid size={{ xs: 12 }}>
      <ImageTable
        project={project}
        batch={batch}
        imageSchema={imageSchema}
        actions={[
          {
            action: Action.RETRY,
            onAction: handleRetryAction,
            enabled: handleRetryEnabled,
          },
        ]}
        onRowsRetry={handleImagesRetry}
        refresh={batch.status === BatchStatus.IMAGE_PRE_PROCESSING}
      />
    </Grid>
  )
}
