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

import { Link, LinearProgress, Stack, Tooltip, Typography } from '@mui/material'
import Button from '@mui/material/Button'
import Grid from '@mui/material/Grid'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import React, { type ReactElement } from 'react'
import { useNavigate } from 'react-router-dom'
import { ImageTable, isImageStuck } from 'src/components/table/image_table'
import { useError } from 'src/contexts/error/error_context'
import { Action } from 'src/models/action'
import { Batch } from 'src/models/batch'
import { BatchStatus } from 'src/models/batch_status'
import { ImageStatus } from 'src/models/image_status'
import { Image } from 'src/models/item'
import type { Project } from 'src/models/project'
import batchApi from 'src/services/api/batch.api'
import configApi from 'src/services/api/config_api'
import itemApi from 'src/services/api/item_api'
import { queryKeys } from 'src/services/query_keys'
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
  const navigate = useNavigate()
  const [starting, setStarting] = React.useState(false)
  const validationQuery = useQuery({
    queryKey: queryKeys.batch.validation(batch.uid),
    queryFn: async () => {
      return await batchApi.getValidation(batch.uid)
    },
  })

  const startProjectMutation = useMutation({
    mutationFn: (batchUid: string) => {
      return batchApi.process(batchUid)
    },
    onSuccess: (updatedBatch) => {
      queryClient.setQueryData(queryKeys.batch.detail(batch.uid), updatedBatch)
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
        <Stack spacing={1} direction="column" sx={{ mt: 1 }}>
          <Typography>
            Batch contains {validationQuery.data.nonValidItems.length} non valid items
          </Typography>
          <Stack
            spacing={0.5}
            direction="column"
            sx={{ maxHeight: '40vh', overflowY: 'auto' }}
          >
            {validationQuery.data.nonValidItems.map((item) => (
              <Link
                key={item.uid}
                component="button"
                underline="hover"
                sx={{ textAlign: 'left' }}
                onClick={() =>
                  navigate(`../curate_batch?openItem=${item.uid}`)
                }
              >
                {item.identifier}
              </Link>
            ))}
          </Stack>
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
  const { showError } = useError()
  const imageSchema = Object.values(rootSchema.images)[0]
  const configQuery = useQuery({
    queryKey: queryKeys.config.all,
    queryFn: configApi.getConfig,
    staleTime: Infinity,
  })
  const stuckThreshold = configQuery.data?.stuckProcessingThresholdSeconds ?? 3600

  const handleRetryAction = (image: Image): void => {
    itemApi.retry([image.uid]).catch((error) => {
      showError('Failed to retry image', error)
    })
  }

  const handleRetryEnabled = (image: Image): boolean => {
    if (
      image.status === ImageStatus.DOWNLOADING_FAILED ||
      image.status === ImageStatus.PRE_PROCESSING_FAILED ||
      image.status === ImageStatus.POST_PROCESSING_FAILED
    ) {
      return true
    }
    return isImageStuck(image, stuckThreshold)
  }

  const handleImagesRetry = (imageUids: string[]): void => {
    itemApi.retry(imageUids).catch((error) => {
      showError('Failed to retry images', error)
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
        refresh={batch.status === BatchStatus.IMAGE_POST_PROCESSING}
      />
    </Grid>
  )
}
