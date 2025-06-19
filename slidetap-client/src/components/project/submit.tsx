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
import Grid from '@mui/material/Grid'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import React, { type ReactElement } from 'react'
import type { Project } from 'src/models/project'
import { ProjectStatus } from 'src/models/project_status'
import projectApi from 'src/services/api/project_api'
import DisplayProjectValidation from './batch/display_project_validation'

interface ExportProps {
  project: Project
}

function Export({ project }: ExportProps): ReactElement {
  const queryClient = useQueryClient()
  const [started, setStarted] = React.useState(false)
  const validationQuery = useQuery({
    queryKey: ['projectValidation', project.uid],
    queryFn: async () => {
      return await projectApi.getValidation(project.uid)
    },
  })
  const handleSubmitProject = (): void => {
    setStarted(true)
    projectApi
      .export(project.uid)
      .then((updatedProject) => {
        queryClient.setQueryData(['project', project.uid], updatedProject)
      })
      .catch((x) => {
        console.error('Failed to submit project', x)
      })
  }
  if (validationQuery.data === undefined) {
    return <LinearProgress />
  }
  const isNotValid = validationQuery.data === undefined || !validationQuery.data.valid

  return (
    <Grid container spacing={1} justifyContent="flex-start" alignItems="flex-start">
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
    </Grid>
  )
}

export default Export
