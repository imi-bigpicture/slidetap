import React, { type ReactElement, Fragment } from 'react'
import { Box, Stack, TextField } from '@mui/material'
import type { Project } from 'models/project'
import StepHeader from 'components/step_header'
import { ProjectStatusStrings } from 'models/status'

interface OverviewProps {
  project: Project
}

export default function Overview({ project }: OverviewProps): ReactElement {
  return (
    <Fragment>
      <StepHeader title="Project overview" />
      <br />
      <Box sx={{ width: 300 }}>
        <Stack spacing={2}>
          <TextField
            label="Project id"
            defaultValue={project.uid === '' ? 'N/A' : project.uid}
            InputProps={{ readOnly: true }}
          />
          <TextField
            label="Project name"
            defaultValue={project.name}
            InputProps={{ readOnly: true }}
          />
          <TextField
            label="Project status"
            defaultValue={ProjectStatusStrings[project.status]}
            InputProps={{ readOnly: true }}
          />
        </Stack>
      </Box>
    </Fragment>
  )
}
