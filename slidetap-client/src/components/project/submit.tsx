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

import { Stack, Tooltip } from '@mui/material'
import Button from '@mui/material/Button'
import Grid from '@mui/material/Unstable_Grid2/Grid2'
import StepHeader from 'components/step_header'
import type { Project, ProjectValidation } from 'models/project'
import { ProjectStatus } from 'models/status'
import React, { useEffect, type ReactElement } from 'react'
import projectApi from 'services/api/project_api'

interface ExportProps {
  project: Project
  setProject: React.Dispatch<React.SetStateAction<Project | undefined>>
}

function Export({ project, setProject }: ExportProps): ReactElement {
  const [validation, setValidation] = React.useState<ProjectValidation>()
  useEffect(() => {
    const getValidation = (projectUid: string): void => {
      projectApi
        .getValidation(projectUid)
        .then((responseValidation) => {
          setValidation(responseValidation)
        })
        .catch((x) => {
          console.error('Failed to get validation', x)
        })
    }
    getValidation(project.uid)
  }, [project.uid])
  const handleSubmitProject = (e: React.MouseEvent<HTMLElement>): void => {
    projectApi
      .export(project.uid)
      .then((updatedProject) => {
        setProject(updatedProject)
      })
      .catch((x) => {
        console.error('Failed to submit project', x)
      })
  }
  const isNotValid = validation === undefined || !validation.is_valid

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
                project.status !== ProjectStatus.IMAGE_POST_PROCESSING_COMPLETE
              }
              onClick={handleSubmitProject}
            >
              Submit
            </Button>
          </Stack>
        </Tooltip>
      </Grid>
    </Grid>
  )
}

export default Export
