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

import { LinearProgress, Stack, Tooltip, Typography } from '@mui/material'
import Button from '@mui/material/Button'
import Grid from '@mui/material/Grid'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import React, { type ReactElement } from 'react'
import { ImageTable } from 'src/components/table/image_table'
import { Action } from 'src/models/action'
import { Batch } from 'src/models/batch'
import { BatchStatus } from 'src/models/batch_status'
import { ImageStatus } from 'src/models/image_status'
import { Image } from 'src/models/item'
import type { Project } from 'src/models/project'
import batchApi from 'src/services/api/batch.api'
import itemApi from 'src/services/api/item_api'
import { useSchemaContext } from '../../../contexts/schema/schema_context'

interface ProcessImagesProps {
  project: Project
  batch: Batch
}

function ProcessImages({ project, batch }: ProcessImagesProps): ReactElement {
  return (
    <Grid container spacing={1} justifyContent="flex-start" alignItems="flex-start">
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

  const startProjectMutation = useMutation({
    mutationFn: (batchUid: string) => {
      return batchApi.process(batchUid)
    },
    onSuccess: (updatedBatch) => {
      queryClient.setQueryData(['batch', batch.uid], updatedBatch)
    },
  })

  const handleStartProject = (): void => {
    setStarting(true)
    startProjectMutation.mutate(batch.uid)
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
      {isNotValid && validationQuery.data !== undefined && (
        <Stack spacing={1} direction="column">
          <Typography>
            Batch contains {validationQuery.data.nonValidItems.length} non valid items
          </Typography>
        </Stack>
      )}
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
  const imageSchema = Object.values(rootSchema.images)[0]

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
        project={project}
        batch={batch}
        imageSchema={imageSchema}
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
        refresh={batch.status === BatchStatus.IMAGE_POST_PROCESSING}
      />
    </Grid>
  )
}
