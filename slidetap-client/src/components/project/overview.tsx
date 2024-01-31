import { Stack, TextField } from '@mui/material'
import Grid from '@mui/material/Unstable_Grid2/Grid2'
import StepHeader from 'components/step_header'
import type { Project } from 'models/project'
import { ProjectStatusStrings } from 'models/status'
import React from 'react'

interface OverviewProps {
  project: Project
}

export default function Overview({ project }: OverviewProps): React.ReactElement {
  return (
    <Grid container spacing={1} justifyContent="flex-start" alignItems="flex-start">
      <Grid xs={12}>
        <StepHeader title="Project overview" />
      </Grid>
      <Grid xs={4}>
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
      </Grid>
    </Grid>
  )
}
