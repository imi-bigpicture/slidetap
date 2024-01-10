import React, { type ReactElement, Fragment } from 'react'
import Button from '@mui/material/Button'
import projectApi from 'services/api/project_api'
import type { Project } from 'models/project'
import { Box, Stack, TextField } from '@mui/material'
import StepHeader from 'components/step_header'

interface ProcessProps {
  project: Project
  nextView: string
  changeView: (to: string) => void
}

function Process({ project, nextView, changeView }: ProcessProps): ReactElement {
  const handleStartProject = (e: React.MouseEvent<HTMLElement>): void => {
    projectApi.process(project.uid).catch((x) => {
      console.error('Failed to start project', x)
    })
    changeView(nextView)
  }

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
          <Button onClick={handleStartProject}>Start</Button>
        </Stack>
      </Box>
    </Fragment>
  )
}

export default Process
