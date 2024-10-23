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

import { Grid, LinearProgress, Stack, Tooltip } from '@mui/material'
import Button from '@mui/material/Button'
import { useQuery } from '@tanstack/react-query'
import StepHeader from 'components/step_header'
import type { Project } from 'models/project'
import { ProjectStatus } from 'models/status'
import React, { type ReactElement } from 'react'
import projectApi from 'services/api/project_api'
import DisplayProjectValidation from './display_project_validation'

interface ExportProps {
  project: Project
  setProject: (project: Project) => void
}

function Export({ project, setProject }: ExportProps): ReactElement {
  const [started, setStarted] = React.useState(false)
  const validationQuery = useQuery({
    queryKey: ['validation', project.uid],
    queryFn: async () => {
      return await projectApi.getValidation(project.uid)
    },
  })
  const handleSubmitProject = (e: React.MouseEvent<HTMLElement>): void => {
    setStarted(true)
    projectApi
      .export(project.uid)
      .then((updatedProject) => {
        setProject(updatedProject)
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
      <Grid xs={12}>
        <StepHeader
          title="Submit"
          description="Submit exported images and metadata to destination."
        />
      </Grid>

      <Grid xs={4}>
        <Tooltip
          title={
            isNotValid ? 'Project contains items that are not yet valid' : undefined
          }
        >
          <Stack>
            <Button
              disabled={
                isNotValid ||
                project.status !== ProjectStatus.IMAGE_POST_PROCESSING_COMPLETE ||
                started
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
