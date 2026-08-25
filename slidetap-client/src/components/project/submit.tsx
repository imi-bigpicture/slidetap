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
  const [confirmingPseudonyms, setConfirmingPseudonyms] = React.useState(false)
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
  })
  const repseudonymizeMutation = useMutation({
    mutationFn: (projectUid: string) => {
      return projectApi.repseudonymize(projectUid)
    },
    onSuccess: () => {
      // Every item now says something else about itself, and the pseudonym is
      // what the tables show of it where the curator is reading pseudonyms.
      void queryClient.invalidateQueries({ queryKey: queryKeys.item.all })
    },
  })
  const handleSubmitProject = (): void => {
    setStarted(true)
    submitProjectMutation.mutate(project.uid)
  }
  const handleRepseudonymize = (): void => {
    setConfirmingPseudonyms(false)
    repseudonymizeMutation.mutate(project.uid)
  }
  if (validationQuery.data === undefined) {
    return <LinearProgress />
  }
  const isNotValid = validationQuery.data === undefined || !validationQuery.data.valid
  const isCompleted = project.status === ProjectStatus.COMPLETED

  return (
    <Grid container spacing={1} sx={{ justifyContent: 'flex-start', alignItems: 'flex-start' }}>
      {/* <Grid size={{ xs: 12 }}>
        <StepHeader
          title="Submit"
          description="Submit exported images and metadata to destination."
        />
      </Grid> */}

      <Grid size={{ xs: 4 }}>
        <Tooltip
          title={
            isNotValid ? 'Project contains items that are not yet valid' : undefined
          }
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
            dataset that has to go out unlinkable to what went out before. Submit the
            project afterwards to write the metadata under them; images already written
            to the outbox carry the old pseudonyms inside their files until they are
            written again.
          </Typography>
          <Tooltip
            title={isCompleted ? undefined : 'Only a completed project can be given new pseudonyms'}
          >
            <Stack>
              <Button
                disabled={!isCompleted || repseudonymizeMutation.isPending}
                onClick={() => {
                  setConfirmingPseudonyms(true)
                }}
              >
                New pseudonyms
              </Button>
            </Stack>
          </Tooltip>
          {repseudonymizeMutation.isSuccess && (
            <Alert severity="success">
              {repseudonymizeMutation.data.changed} items were given a new pseudonym.
              Submit the project to write the metadata under them.
            </Alert>
          )}
          {repseudonymizeMutation.isError && (
            <Alert severity="error">{refusal(repseudonymizeMutation.error)}</Alert>
          )}
        </Stack>
      </Grid>
      <Dialog
        open={confirmingPseudonyms}
        onClose={() => {
          setConfirmingPseudonyms(false)
        }}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>Give the dataset new pseudonyms?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Every item of <strong>{project.name}</strong> is given a pseudonym it has
            not had before. What has already been submitted keeps the old ones, and
            nothing here says which new pseudonym took which old one&apos;s place.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setConfirmingPseudonyms(false)
            }}
          >
            Cancel
          </Button>
          <Button onClick={handleRepseudonymize}>New pseudonyms</Button>
        </DialogActions>
      </Dialog>
    </Grid>
  )
}

export default Export
