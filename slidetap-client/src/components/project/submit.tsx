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

import {
  Alert,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  Stack,
  Tooltip,
  Typography,
} from '@mui/material'
import Button from '@mui/material/Button'
import Grid from '@mui/material/Grid'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import React, { type ReactElement } from 'react'
import { useProjectActions } from 'src/contexts/project_actions/project_actions_context'
import type { Batch } from 'src/models/batch'
import { BatchStatus, BatchStatusStrings } from 'src/models/batch_status'
import type { Project } from 'src/models/project'
import { ProjectStatus } from 'src/models/project_status'
import { ApiError } from 'src/services/api/api_methods'
import batchApi from 'src/services/api/batch.api'
import projectApi from 'src/services/api/project_api'
import { queryKeys } from 'src/services/query_keys'
import DisplayProjectValidation from './batch/display_project_validation'

interface ExportProps {
  project: Project
}

/** What the server said it would not do, rather than that something failed. */
function refusal(error: Error | null): string | undefined {
  if (error === null) {
    return undefined
  }
  return error instanceof ApiError ? (error.body ?? error.message) : error.message
}

/** Statuses a batch can no longer change from by itself, and that need no
 * storing: removed from the project, or failed. */
const SETTLED_ELSEWHERE = new Set([
  BatchStatus.DELETING,
  BatchStatus.DELETED,
  BatchStatus.FAILED,
])

/** A batch, where it stands, and while its images are stored or once they
 * are, how many of them are in the outbox. */
function BatchStoring({ batch }: { batch: Batch }): ReactElement {
  const storing = batch.status === BatchStatus.IMAGE_STORING
  const shown = storing || batch.status === BatchStatus.COMPLETED
  const progressQuery = useQuery({
    queryKey: queryKeys.batch.storing(batch.uid),
    queryFn: async () => await batchApi.getStoringProgress(batch.uid),
    enabled: shown,
    refetchInterval: storing ? 2000 : false,
  })
  const status = batch.statusMessage
    ? `${BatchStatusStrings[batch.status]}: ${batch.statusMessage}`
    : BatchStatusStrings[batch.status]
  const progress = shown ? progressQuery.data : undefined
  // Every image tried, and some failed: the worker is done with the batch, and
  // it waits for them to be retried or taken out.
  const stopped =
    progress !== undefined &&
    storing &&
    progress.failed > 0 &&
    progress.stored + progress.failed === progress.total
  return (
    <Stack sx={{ width: '100%' }} spacing={0.5}>
      <ListItemText primary={batch.name} secondary={status} />
      {progress !== undefined && progress.total > 0 && (
        <>
          <LinearProgress
            variant="determinate"
            value={(100 * progress.stored) / progress.total}
            color={progress.failed > 0 ? 'warning' : 'primary'}
          />
          <Typography variant="caption" color="text.secondary">
            {progress.stored} of {progress.total} images stored
            {progress.failed > 0 && `, ${progress.failed} failed`}
          </Typography>
        </>
      )}
      {stopped && (
        <Alert severity="warning">
          Storing stopped with {progress.failed} image
          {progress.failed === 1 ? '' : 's'} not stored. Retry{' '}
          {progress.failed === 1 ? 'it' : 'them'}, or take{' '}
          {progress.failed === 1 ? 'it' : 'them'} out, on the batch's Post-process page,
          then resume storing.
        </Alert>
      )}
    </Stack>
  )
}

/**
 * Hands the project over in two steps: the images of every locked batch are
 * stored to the outbox, and once every batch is there, the metadata is
 * exported beside them.
 *
 * Stored for the project rather than as each batch is locked, so that a batch
 * reopened until then leaves nothing behind in a bundle already handed over.
 */
function Export({ project }: ExportProps): ReactElement {
  const queryClient = useQueryClient()
  const [started, setStarted] = React.useState(false)
  // Refused for a project on a root schema the export does not support.
  const { edit: canExport } = useProjectActions()
  const validationQuery = useQuery({
    queryKey: queryKeys.project.validation(project.uid),
    queryFn: async () => {
      return await projectApi.getValidation(project.uid)
    },
  })
  const batchesQuery = useQuery({
    queryKey: queryKeys.batch.list(project.uid),
    queryFn: async () => await batchApi.getBatches(project.uid),
    // Followed while images are being stored, which a worker does.
    refetchInterval: (query) =>
      query.state.data?.some((batch) => batch.status === BatchStatus.IMAGE_STORING)
        ? 2000
        : false,
  })
  const storeImagesMutation = useMutation({
    mutationFn: async (projectUid: string) => await projectApi.storeImages(projectUid),
    meta: { handlesError: true },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.batch.all })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.project.detail(project.uid),
      })
    },
  })
  const submitProjectMutation = useMutation({
    mutationFn: (projectUid: string) => {
      return projectApi.export(projectUid)
    },
    onSuccess: (updatedProject) => {
      queryClient.setQueryData(queryKeys.project.detail(project.uid), updatedProject)
    },
    onError: () => {
      // Refused rather than started: the button is what says whether it can be
      // pressed again, and nothing was set going.
      setStarted(false)
    },
  })
  const handleSubmitProject = (): void => {
    setStarted(true)
    submitProjectMutation.mutate(project.uid)
  }
  if (validationQuery.data === undefined || batchesQuery.data === undefined) {
    return <LinearProgress />
  }
  const isNotValid = !validationQuery.data.valid
  const batches = batchesQuery.data.filter(
    (batch) => !SETTLED_ELSEWHERE.has(batch.status),
  )
  const count = (status: BatchStatus): number =>
    batches.filter((batch) => batch.status === status).length
  const locked = count(BatchStatus.LOCKED)
  const storing = count(BatchStatus.IMAGE_STORING)
  const stored = count(BatchStatus.COMPLETED)
  const notLocked = batches.length - locked - storing - stored
  const allLocked = project.status === ProjectStatus.COMPLETED && notLocked === 0
  const allStored = allLocked && stored === batches.length && batches.length > 0
  const canStore = canExport && allLocked && (locked > 0 || storing > 0)
  const submitBlocked = !canExport
    ? 'The project is on a schema that cannot be exported'
    : !allStored
      ? 'The images of every batch have to be stored to the outbox first'
      : isNotValid
        ? 'Project contains items that are not yet valid'
        : undefined

  return (
    <Grid
      container
      spacing={2}
      sx={{ justifyContent: 'flex-start', alignItems: 'flex-start' }}
    >
      <Grid size={{ xs: 6 }}>
        <Stack spacing={1}>
          <Typography variant="h6">1. Store images to outbox</Typography>
          <Typography variant="body2" color="text.secondary">
            Copies the images of every locked batch to the outbox. After this a batch
            can no longer be reopened. It can be started once every batch is locked.
          </Typography>
          <List dense disablePadding>
            {batches.map((batch) => (
              <ListItem key={batch.uid} disableGutters>
                <BatchStoring batch={batch} />
              </ListItem>
            ))}
          </List>
          {notLocked > 0 && (
            <Alert severity="info">
              {notLocked} {notLocked === 1 ? 'batch is' : 'batches are'} not locked yet.
              Lock {notLocked === 1 ? 'it' : 'them'} from the batch's Lock page.
            </Alert>
          )}
          <Tooltip
            title={
              storing > 0 && locked === 0
                ? 'Resumes storing that stopped part-way. Wait while it is still running.'
                : undefined
            }
          >
            <span>
              <Button
                disabled={!canStore || storeImagesMutation.isPending}
                onClick={() => storeImagesMutation.mutate(project.uid)}
              >
                {storing > 0 && locked === 0 ? 'Resume storing' : 'Store images'}
              </Button>
            </span>
          </Tooltip>
          {storeImagesMutation.isError && (
            <Alert severity="error">{refusal(storeImagesMutation.error)}</Alert>
          )}
        </Stack>
      </Grid>
      <Grid size={{ xs: 6 }}>
        <Stack spacing={1}>
          <Typography variant="h6">2. Export metadata</Typography>
          <Typography variant="body2" color="text.secondary">
            Writes the metadata beside the stored images, completing the bundle.
          </Typography>
          <Tooltip title={submitBlocked}>
            <span>
              <Button
                disabled={submitBlocked !== undefined || started}
                onClick={handleSubmitProject}
              >
                Submit
              </Button>
            </span>
          </Tooltip>
          {submitProjectMutation.isError && (
            <Alert severity="error">{refusal(submitProjectMutation.error)}</Alert>
          )}
        </Stack>
      </Grid>
      {isNotValid && (
        <Grid size={{ xs: 12 }}>
          {DisplayProjectValidation({ validation: validationQuery.data })}
        </Grid>
      )}
    </Grid>
  )
}

export default Export
