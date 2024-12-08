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

import { Button, Stack, TextField } from '@mui/material'
import Grid from '@mui/material/Grid2'
import StepHeader from 'components/step_header'
import type { Project } from 'models/project'
import { ProjectStatusStrings } from 'models/project_status'
import React from 'react'
import projectApi from 'services/api/project_api'

interface OverviewProps {
  project: Project
}

export default function Overview({ project }: OverviewProps): React.ReactElement {
  return (
    <Grid container spacing={1} justifyContent="flex-start" alignItems="flex-start">
      <Grid size={{ xs: 12 }}>
        <StepHeader title="Project overview" />
      </Grid>
      <Grid size={{ xs: 4 }}>
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
          <Button
            onClick={() => {
              projectApi.validateProject(project.uid).catch((error) => {
                console.error(error)
              })
            }}
          >
            Revaluate
          </Button>
        </Stack>
      </Grid>
    </Grid>
  )
}
