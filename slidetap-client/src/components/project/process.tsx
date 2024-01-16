import { Box, Stack, TextField, Tooltip } from '@mui/material'
import Button from '@mui/material/Button'
import StepHeader from 'components/step_header'
import type { Project, ProjectValidation } from 'models/project'
import React, { Fragment, useEffect, type ReactElement } from 'react'
import projectApi from 'services/api/project_api'

interface ProcessProps {
  project: Project
  nextView: string
  changeView: (to: string) => void
}

function Process({ project, nextView, changeView }: ProcessProps): ReactElement {
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

  const handleStartProject = (e: React.MouseEvent<HTMLElement>): void => {
    projectApi.process(project.uid).catch((x) => {
      console.error('Failed to start project', x)
    })
    changeView(nextView)
  }
  const isNotValid = validation === undefined || !validation.is_valid
  return (
    <Fragment>
      <StepHeader
        title="Process"
        description="Process export of project. This disables further changes in project."
      />
      <Box sx={{ width: 300 }}>
        <Stack spacing={2}>
          {project.items.map((itemSchema, index) => (
            <TextField
              key={index}
              label={itemSchema.schema.name}
              value={itemSchema.count}
              InputProps={{ readOnly: true }}
            />
          ))}
          <Tooltip
            title={
              isNotValid ? 'Project contains items that are not yet valid' : undefined
            }
          >
            <Stack>
              <Button disabled={isNotValid} onClick={handleStartProject}>
                Start
              </Button>
            </Stack>
          </Tooltip>
        </Stack>
      </Box>
    </Fragment>
  )
}

export default Process
