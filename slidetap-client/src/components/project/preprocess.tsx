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

import { Stack, TextField } from '@mui/material'
import Button from '@mui/material/Button'
import Grid from '@mui/material/Unstable_Grid2/Grid2'
import StepHeader from 'components/step_header'
import type { Project } from 'models/project'
import React from 'react'
import projectApi from 'services/api/project_api'

interface PreProcessImagesProps {
  project: Project
  setProject: React.Dispatch<React.SetStateAction<Project | undefined>>
  nextView: string
  changeView: (to: string) => void
}

function PreProcessImages({
  project,
  setProject,
  nextView,
  changeView,
}: PreProcessImagesProps): React.ReactElement {
  const handleStartPreProcessingImages = (e: React.MouseEvent<HTMLElement>): void => {
    projectApi
      .preprocess(project.uid)
      .then((updatedProject) => {
        setProject(updatedProject)
      })
      .catch((x) => {
        console.error('Failed to download project', x)
      })
    changeView(nextView)
  }

  return (
    <Grid container spacing={1} justifyContent="flex-start" alignItems="flex-start">
      <Grid xs={12}>
        <StepHeader title="Pre-process" description="Pre-process images in project." />
      </Grid>

      <Grid xs={4}>
        <Stack spacing={2}>
          {project.items.map((itemSchema, index) => (
            <TextField
              key={index}
              label={itemSchema.schema.name}
              value={itemSchema.count}
              InputProps={{ readOnly: true }}
            />
          ))}
          <Button onClick={handleStartPreProcessingImages}>Pre-process</Button>
        </Stack>
      </Grid>
    </Grid>
  )
}

export default PreProcessImages
