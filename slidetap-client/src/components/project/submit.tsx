import { Stack, Tooltip } from '@mui/material'
import Button from '@mui/material/Button'
import Grid from '@mui/material/Unstable_Grid2/Grid2'
import StepHeader from 'components/step_header'
import type { Project, ProjectValidation } from 'models/project'
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
            <Button disabled={isNotValid} onClick={handleSubmitProject}>
              Submit
            </Button>
          </Stack>
        </Tooltip>
      </Grid>
    </Grid>
  )
}

export default Export
