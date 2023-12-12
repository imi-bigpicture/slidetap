import React, { type ReactElement } from 'react'
import Button from '@mui/material/Button'
import projectApi from 'services/api/project_api'
import { Box } from '@mui/system'
import type { Project } from 'models/project'
import StepHeader from 'components/step_header'

interface ExportProps {
  project: Project
}

function Export({ project }: ExportProps): ReactElement {
  const handleSubmitProject = (e: React.MouseEvent<HTMLElement>): void => {
    projectApi.export(project.uid).catch((x) => {
      console.error('Failed to submit project', x)
    })
  }

  return (
    <React.Fragment>
      <StepHeader
        title="Submit"
        description="Submit exported images and metadata to destination."
      />
      <Box sx={{ width: 300 }}>
        <Button onClick={handleSubmitProject}>Submit</Button>
      </Box>
    </React.Fragment>
  )
}

export default Export
