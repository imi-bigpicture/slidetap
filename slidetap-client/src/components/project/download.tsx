import { Stack, TextField } from '@mui/material'
import Button from '@mui/material/Button'
import Grid from '@mui/material/Unstable_Grid2/Grid2'
import StepHeader from 'components/step_header'
import type { Project } from 'models/project'
import React from 'react'
import projectApi from 'services/api/project_api'

interface DownloadImagesProps {
  project: Project
  setProject: React.Dispatch<React.SetStateAction<Project | undefined>>
  nextView: string
  changeView: (to: string) => void
}

function DownloadImages({
  project,
  setProject,
  nextView,
  changeView,
}: DownloadImagesProps): React.ReactElement {
  const handleStartDownloadingImages = (e: React.MouseEvent<HTMLElement>): void => {
    projectApi
      .download(project.uid)
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
        <StepHeader title="Download" description="Download images in project." />
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
          <Button onClick={handleStartDownloadingImages}>Pre-process</Button>
        </Stack>
      </Grid>
    </Grid>
  )
}

export default DownloadImages
