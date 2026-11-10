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
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  Typography,
} from '@mui/material'
import Button from '@mui/material/Button'
import {
  queryOptions,
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import React, { type ReactElement } from 'react'
import { useProjectActions } from 'src/contexts/project_actions/project_actions_context'
import { useAllowsBatchExport } from 'src/hooks/use_allows_batch_export'
import { type Batch, type BatchStoringProgress, storedAlone } from 'src/models/batch'
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

/** How the project is handed over: as a whole, or a batch at a time. */
type ExportMode = 'project' | 'batch'

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

/** Statuses a batch has once its images are in the outbox. */
const IN_THE_OUTBOX = new Set([
  BatchStatus.COMPLETED,
  BatchStatus.EXPORTING,
  BatchStatus.EXPORTED,
])

/** Batch status, with the reason if it failed or its export was refused. */
function BatchStatusCell({ batch }: { batch: Batch }): ReactElement {
  return (
    <TableCell>
      {BatchStatusStrings[batch.status]}
      {batch.statusMessage && (
        <Typography variant="caption" color="text.secondary" component="div">
          {batch.statusMessage}
        </Typography>
      )}
    </TableCell>
  )
}

/** Storing progress of a batch, polled while it stores. Keyed by status so a
 * fresh count is fetched when the status changes. */
function storingProgressQuery(batch: Batch) {
  const storing = batch.status === BatchStatus.IMAGE_STORING
  return queryOptions({
    queryKey: [...queryKeys.batch.storing(batch.uid), batch.status],
    queryFn: async () => await batchApi.getStoringProgress(batch.uid),
    enabled: storing || IN_THE_OUTBOX.has(batch.status),
    refetchInterval: storing ? 2000 : false,
  })
}

/** Whether storing stopped part-way: every image tried and some failed, so it
 * waits to be resumed. False while progress is unknown. */
function storingStopped(
  batch: Batch,
  progress: BatchStoringProgress | undefined,
): boolean {
  return (
    progress !== undefined &&
    batch.status === BatchStatus.IMAGE_STORING &&
    progress.failed > 0 &&
    progress.stored + progress.failed === progress.total
  )
}

/** Images of a batch in the outbox, shown from when storing starts. */
function StoringCell({ batch }: { batch: Batch }): ReactElement {
  const progressQuery = useQuery(storingProgressQuery(batch))
  const progress = progressQuery.data
  const stopped = storingStopped(batch, progress)
  return (
    <TableCell sx={{ minWidth: 200 }}>
      {progress !== undefined && progress.total > 0 && (
        <Stack spacing={0.5}>
          <LinearProgress
            variant="determinate"
            value={(100 * progress.stored) / progress.total}
            color={progress.failed > 0 ? 'warning' : 'primary'}
          />
          <Typography variant="caption" color="text.secondary">
            {progress.stored} of {progress.total} stored
            {progress.failed > 0 && `, ${progress.failed} failed`}
          </Typography>
        </Stack>
      )}
      {stopped && progress !== undefined && (
        <Alert severity="warning" sx={{ mt: 0.5 }}>
          Storing stopped with {progress.failed} image
          {progress.failed === 1 ? '' : 's'} not stored. Retry{' '}
          {progress.failed === 1 ? 'it' : 'them'}, or take{' '}
          {progress.failed === 1 ? 'it' : 'them'} out, on the batch's Post-process page,
          then resume storing.
        </Alert>
      )}
    </TableCell>
  )
}

/** Next step for a batch exported on its own: store images, resume storing or
 * export metadata. */
function BatchActionCell({
  batch,
  canExport,
}: {
  batch: Batch
  canExport: boolean
}): ReactElement {
  const queryClient = useQueryClient()
  const onSettled = (): void => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.batch.all })
    void queryClient.invalidateQueries({ queryKey: queryKeys.project.all })
  }
  const storeMutation = useMutation({
    mutationFn: async (batchUid: string) => await batchApi.storeAlone(batchUid),
    meta: { handlesError: true },
    onSettled,
  })
  const exportMutation = useMutation({
    mutationFn: async (batchUid: string) => await batchApi.exportAlone(batchUid),
    meta: { handlesError: true },
    onSettled,
  })
  const progressQuery = useQuery(storingProgressQuery(batch))
  const pending = storeMutation.isPending || exportMutation.isPending
  const alone = storedAlone(batch)
  const error = storeMutation.error ?? exportMutation.error
  let action: ReactElement | undefined
  if (batch.status === BatchStatus.LOCKED) {
    action = (
      <Tooltip title="After this the batch can no longer be reopened.">
        <span>
          <Button
            size="small"
            disabled={!canExport || pending}
            onClick={() => storeMutation.mutate(batch.uid)}
          >
            Store images
          </Button>
        </span>
      </Tooltip>
    )
  } else if (alone && storingStopped(batch, progressQuery.data)) {
    action = (
      <Tooltip title="Stores again what failed to store, once it has been retried or taken out.">
        <span>
          <Button
            size="small"
            disabled={!canExport || pending}
            onClick={() => storeMutation.mutate(batch.uid)}
          >
            Resume storing
          </Button>
        </span>
      </Tooltip>
    )
  } else if (alone && batch.status === BatchStatus.IMAGE_STORING) {
    action = (
      <Button size="small" disabled>
        Storing…
      </Button>
    )
  } else if (alone && batch.status === BatchStatus.COMPLETED) {
    action = (
      <Button
        size="small"
        disabled={!canExport || pending}
        onClick={() => exportMutation.mutate(batch.uid)}
      >
        Export metadata
      </Button>
    )
  } else if (!IN_THE_OUTBOX.has(batch.status)) {
    action = (
      <Typography variant="body2" color="text.secondary">
        Lock the batch first
      </Typography>
    )
  }
  return (
    <TableCell>
      {action}
      {error !== null && (
        <Alert severity="error" sx={{ mt: 0.5 }}>
          {refusal(error)}
        </Alert>
      )}
    </TableCell>
  )
}

/** The project's batches. In batch mode also their bundle and next step. */
function BatchTable({
  batches,
  mode,
  canExport,
}: {
  batches: Batch[]
  mode: ExportMode
  canExport: boolean
}): ReactElement {
  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Batch</TableCell>
            <TableCell>Created</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>Status updated</TableCell>
            <TableCell>Images in the outbox</TableCell>
            {mode === 'batch' && <TableCell>Bundle</TableCell>}
            {mode === 'batch' && <TableCell>Next step</TableCell>}
          </TableRow>
        </TableHead>
        <TableBody>
          {batches.length === 0 && (
            <TableRow>
              <TableCell colSpan={mode === 'batch' ? 7 : 5}>
                The project has no batches to export.
              </TableCell>
            </TableRow>
          )}
          {batches.map((batch) => (
            <TableRow key={batch.uid}>
              <TableCell>{batch.name}</TableCell>
              <TableCell sx={{ whiteSpace: 'nowrap' }}>
                {new Date(batch.created).toLocaleString('en-gb')}
              </TableCell>
              <BatchStatusCell batch={batch} />
              <TableCell sx={{ whiteSpace: 'nowrap' }}>
                {batch.statusUpdated === null
                  ? ''
                  : new Date(batch.statusUpdated).toLocaleString('en-gb')}
              </TableCell>
              <StoringCell batch={batch} />
              {mode === 'batch' && (
                <TableCell>
                  <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                    {batch.storageFolder ?? ''}
                  </Typography>
                </TableCell>
              )}
              {mode === 'batch' && (
                <BatchActionCell batch={batch} canExport={canExport} />
              )}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

/**
 * Hands the project over, as a whole or a batch at a time.
 *
 * As a whole: the images of every locked batch are stored to the outbox, then
 * the metadata is exported beside them.
 * Stored for the project rather than as each batch is locked, so that a batch
 * reopened until then leaves nothing behind in a bundle already handed over.
 *
 * A batch at a time, where allowed: the same two steps per batch, into its own
 * bundle. The modes do not mix: once a batch is stored one way, so are all.
 */
function Export({ project }: ExportProps): ReactElement {
  const queryClient = useQueryClient()
  const [started, setStarted] = React.useState(false)
  const [chosenMode, setChosenMode] = React.useState<ExportMode>()
  // Refused for a project on a root schema the export does not support.
  const { edit: canExport } = useProjectActions()
  // Batch mode is offered only where the server allows it.
  const allowsBatchExport = useAllowsBatchExport()
  const validationQuery = useQuery({
    queryKey: queryKeys.project.validation(project.uid),
    queryFn: async () => {
      return await projectApi.getValidation(project.uid)
    },
  })
  const batchesQuery = useQuery({
    queryKey: queryKeys.batch.list(project.uid),
    queryFn: async () => await batchApi.getBatches(project.uid),
    // Polled while a worker stores images or exports a batch.
    refetchInterval: (query) =>
      query.state.data?.some(
        (batch) =>
          batch.status === BatchStatus.IMAGE_STORING ||
          batch.status === BatchStatus.EXPORTING,
      )
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
  // Batches storing with the project, to tell running from stopped storing.
  // Shares its queries with the table.
  const storingWithProject = (batchesQuery.data ?? []).filter(
    (batch) => batch.status === BatchStatus.IMAGE_STORING && !storedAlone(batch),
  )
  const storingProgress = useQueries({
    queries: storingWithProject.map(storingProgressQuery),
  })
  const storingRuns = storingWithProject.some(
    (batch, index) => !storingStopped(batch, storingProgress[index]?.data),
  )
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
  const exported = count(BatchStatus.EXPORTING) + count(BatchStatus.EXPORTED)
  const notLocked = batches.length - locked - storing - stored - exported
  const allLocked = project.status === ProjectStatus.COMPLETED && notLocked === 0
  const allStored = allLocked && stored === batches.length && batches.length > 0
  // The modes do not mix: once a batch is stored on its own, all are; once one
  // is stored with the project, none is stored on its own.
  const anyAlone = batches.some(storedAlone)
  const anyWithProject = batches.some(
    (batch) =>
      !storedAlone(batch) &&
      (batch.status === BatchStatus.IMAGE_STORING ||
        batch.status === BatchStatus.COMPLETED),
  )
  const settledMode: ExportMode | undefined = !allowsBatchExport
    ? 'project'
    : anyAlone
      ? 'batch'
      : anyWithProject
        ? 'project'
        : undefined
  const mode: ExportMode = settledMode ?? chosenMode ?? 'project'
  const canStore =
    canExport && !anyAlone && allLocked && !storingRuns && (locked > 0 || storing > 0)
  const storeLabel = storingRuns
    ? '1. Storing…'
    : storing > 0 && locked === 0
      ? '1. Resume storing'
      : '1. Store images'
  const submitBlocked = !canExport
    ? 'The project is on a schema that cannot be exported'
    : anyAlone
      ? 'Batches of the project are exported on their own'
      : !allStored
        ? 'The images of every batch have to be stored to the outbox first'
        : isNotValid
          ? 'Project contains items that are not yet valid'
          : undefined

  return (
    <Stack spacing={2} sx={{ maxWidth: 1200 }}>
      {allowsBatchExport && (
        <Stack spacing={1}>
          <Tooltip
            title={
              settledMode === 'batch'
                ? 'Batches of the project are exported on their own.'
                : settledMode === 'project'
                  ? 'Batches of the project are stored with the project.'
                  : undefined
            }
          >
            <ToggleButtonGroup
              size="small"
              exclusive
              value={mode}
              disabled={settledMode !== undefined}
              onChange={(_, value: ExportMode | null) => {
                if (value !== null) {
                  setChosenMode(value)
                }
              }}
              sx={{ alignSelf: 'flex-start' }}
            >
              <ToggleButton value="project">Export the project</ToggleButton>
              <ToggleButton value="batch">Export batches on their own</ToggleButton>
            </ToggleButtonGroup>
          </Tooltip>
          {settledMode === undefined && (
            <Typography variant="body2" color="text.secondary">
              Choose before storing any images. Once a batch is stored one way, every
              batch of the project is exported that way.
            </Typography>
          )}
        </Stack>
      )}
      {mode === 'project' ? (
        <Typography variant="body2" color="text.secondary">
          Export the project as one bundle once every batch is locked: store the images,
          then export the metadata. A batch cannot be reopened after its images are
          stored.
        </Typography>
      ) : (
        <Typography variant="body2" color="text.secondary">
          Export each locked batch as its own bundle: store its images, then export its
          metadata. A batch cannot be reopened after its images are stored.
        </Typography>
      )}
      <BatchTable batches={batches} mode={mode} canExport={canExport} />
      {mode === 'project' && notLocked > 0 && (
        <Alert severity="info">
          {notLocked} {notLocked === 1 ? 'batch is' : 'batches are'} not locked yet.
          Lock {notLocked === 1 ? 'it' : 'them'} from the batch's Lock page.
        </Alert>
      )}
      {mode === 'project' && (
        <Stack direction="row" spacing={2}>
          <Tooltip
            title={
              !storingRuns && storing > 0 && locked === 0
                ? 'Stores again what failed to store, once it has been retried or taken out.'
                : undefined
            }
          >
            <span>
              <Button
                variant="outlined"
                disabled={!canStore || storeImagesMutation.isPending}
                onClick={() => storeImagesMutation.mutate(project.uid)}
              >
                {storeLabel}
              </Button>
            </span>
          </Tooltip>
          <Tooltip title={submitBlocked}>
            <span>
              <Button
                variant="outlined"
                disabled={submitBlocked !== undefined || started}
                onClick={handleSubmitProject}
              >
                2. Export metadata
              </Button>
            </span>
          </Tooltip>
        </Stack>
      )}
      {storeImagesMutation.isError && (
        <Alert severity="error">{refusal(storeImagesMutation.error)}</Alert>
      )}
      {submitProjectMutation.isError && (
        <Alert severity="error">{refusal(submitProjectMutation.error)}</Alert>
      )}
      {isNotValid && DisplayProjectValidation({ validation: validationQuery.data })}
    </Stack>
  )
}

export default Export
