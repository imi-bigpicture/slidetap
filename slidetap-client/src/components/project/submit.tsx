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
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Divider,
  LinearProgress,
  Stack,
  Tooltip,
  Typography,
} from '@mui/material'
import Button from '@mui/material/Button'
import Grid from '@mui/material/Grid'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import React, { type ReactElement } from 'react'
import type { Project } from 'src/models/project'
import { ProjectStatus } from 'src/models/project_status'
import { ApiError } from 'src/services/api/api_methods'
import projectApi from 'src/services/api/project_api'
import { queryKeys } from 'src/services/query_keys'
import DisplayProjectValidation from './batch/display_project_validation'

interface ExportProps {
  project: Project
}

/** Which of the two the dialog is asking about, or neither. */
type PendingPseudonymAction = 'new' | 'clear' | null

/** What the server said it would not do, rather than that something failed. */
function refusal(error: Error | null): string | undefined {
  if (error === null) {
    return undefined
  }
  return error instanceof ApiError ? (error.body ?? error.message) : error.message
}

function Export({ project }: ExportProps): ReactElement {
  const queryClient = useQueryClient()
  const [started, setStarted] = React.useState(false)
  const [pending, setPending] = React.useState<PendingPseudonymAction>(null)
  const validationQuery = useQuery({
    queryKey: queryKeys.project.validation(project.uid),
    queryFn: async () => {
      return await projectApi.getValidation(project.uid)
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
  // Every item now says something else about itself, and the pseudonym is what
  // the tables show of it where the curator is reading pseudonyms.
  const invalidateItems = (): void => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.item.all })
  }
  const repseudonymizeMutation = useMutation({
    mutationFn: (projectUid: string) => {
      return projectApi.repseudonymize(projectUid)
    },
    onSuccess: invalidateItems,
  })
  const clearPseudonymsMutation = useMutation({
    mutationFn: (projectUid: string) => {
      return projectApi.clearPseudonyms(projectUid)
    },
    onSuccess: invalidateItems,
  })
  const handleSubmitProject = (): void => {
    setStarted(true)
    submitProjectMutation.mutate(project.uid)
  }
  const handleConfirmed = (): void => {
    const action = pending
    setPending(null)
    if (action === 'new') {
      repseudonymizeMutation.mutate(project.uid)
    } else if (action === 'clear') {
      clearPseudonymsMutation.mutate(project.uid)
    }
  }
  if (validationQuery.data === undefined) {
    return <LinearProgress />
  }
  const isNotValid = validationQuery.data === undefined || !validationQuery.data.valid
  const isCompleted = project.status === ProjectStatus.COMPLETED
  const pseudonymsBusy =
    repseudonymizeMutation.isPending || clearPseudonymsMutation.isPending

  return (
    <Grid
      container
      spacing={1}
      sx={{ justifyContent: 'flex-start', alignItems: 'flex-start' }}
    >
      {/* <Grid size={{ xs: 12 }}>
        <StepHeader
          title="Submit"
          description="Submit exported images and metadata to destination."
        />
      </Grid> */}

      <Grid size={{ xs: 4 }}>
        <Tooltip
          title={isNotValid ? 'Project contains items that are not yet valid' : undefined}
        >
          <Stack>
            <Button
              disabled={
                isNotValid || project.status !== ProjectStatus.COMPLETED || started
              }
              onClick={handleSubmitProject}
            >
              Submit
            </Button>
          </Stack>
        </Tooltip>
      </Grid>
      {submitProjectMutation.isError && (
        <Grid size={{ xs: 12 }}>
          <Alert severity="error">{refusal(submitProjectMutation.error)}</Alert>
        </Grid>
      )}
      {isNotValid &&
        validationQuery.data !== undefined &&
        DisplayProjectValidation({ validation: validationQuery.data })}
      <Grid size={{ xs: 12 }}>
        <Divider sx={{ my: 2 }} />
      </Grid>
      <Grid size={{ xs: 6 }}>
        <Stack spacing={1}>
          <Typography variant="subtitle2">Pseudonyms</Typography>
          <Typography variant="body2" color="text.secondary">
            The dataset goes out under the pseudonyms its items were given when they
            were imported, the same ones every time it is submitted. New ones are for a
            dataset that has to go out unlinkable to what went out before; submit it
            afterwards to write the metadata under them. Taking them off instead leaves
            the items standing for nothing that has gone out, and the project cannot be
            submitted again. Images already written to the outbox carry the pseudonyms
            they were written with either way.
          </Typography>
          <Tooltip
            title={
              isCompleted ? undefined : 'Only a completed project can have its pseudonyms changed'
            }
          >
            <Stack direction="row" spacing={1}>
              <Button
                disabled={!isCompleted || pseudonymsBusy}
                onClick={() => {
                  setPending('new')
                }}
              >
                New pseudonyms
              </Button>
              <Button
                color="error"
                disabled={!isCompleted || pseudonymsBusy}
                onClick={() => {
                  setPending('clear')
                }}
              >
                Clear pseudonyms
              </Button>
            </Stack>
          </Tooltip>
          {repseudonymizeMutation.isSuccess && (
            <Alert severity="success">
              {repseudonymizeMutation.data.changed} items were given a new pseudonym.
              Submit the project to write the metadata under them.
            </Alert>
          )}
          {clearPseudonymsMutation.isSuccess && (
            <Alert severity="success">
              {clearPseudonymsMutation.data.changed} items no longer carry a pseudonym.
              The project can no longer be submitted.
            </Alert>
          )}
          {repseudonymizeMutation.isError && (
            <Alert severity="error">{refusal(repseudonymizeMutation.error)}</Alert>
          )}
          {clearPseudonymsMutation.isError && (
            <Alert severity="error">{refusal(clearPseudonymsMutation.error)}</Alert>
          )}
        </Stack>
      </Grid>
      <Dialog
        open={pending !== null}
        onClose={() => {
          setPending(null)
        }}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>
          {pending === 'clear'
            ? 'Take the pseudonyms off the dataset?'
            : 'Give the dataset new pseudonyms?'}
        </DialogTitle>
        <DialogContent>
          <DialogContentText>
            {pending === 'clear' ? (
              <>
                Every item of <strong>{project.name}</strong> loses the pseudonym it
                went out under, and nothing puts one back: the project cannot be
                submitted again. What has already been handed over is not touched, and
                neither is the pseudonym file written beside it, which still maps what
                went out to what it was.
              </>
            ) : (
              <>
                Every item of <strong>{project.name}</strong> is given a pseudonym it
                has not had before. What has already been submitted keeps the old ones,
                and nothing here says which new pseudonym took which old one&apos;s
                place.
              </>
            )}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setPending(null)
            }}
          >
            Cancel
          </Button>
          <Button color={pending === 'clear' ? 'error' : 'primary'} onClick={handleConfirmed}>
            {pending === 'clear' ? 'Clear pseudonyms' : 'New pseudonyms'}
          </Button>
        </DialogActions>
      </Dialog>
    </Grid>
  )
}

export default Export
