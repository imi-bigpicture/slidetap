import React, { type ReactElement, Fragment } from 'react'
import Button from '@mui/material/Button'
import projectApi from 'services/api/project_api'
import type { Project } from 'models/project'
import { Box, Stack, TextField } from '@mui/material'
import StepHeader from 'components/step_header'

interface DownloadImagesProps {
  project: Project
  nextView: string
  changeView: (to: string) => void
}

function DownloadImages({
  project,
  nextView,
  changeView,
}: DownloadImagesProps): ReactElement {
  const handleStartDownloadingImages = (e: React.MouseEvent<HTMLElement>): void => {
    projectApi.download(project.uid).catch((x) => {
      console.error('Failed to download project', x)
    })
    changeView(nextView)
  }

  return (
    <Fragment>
      <StepHeader title="Download" description="Download images in project." />

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
          <Button onClick={handleStartDownloadingImages}>Download</Button>
        </Stack>
      </Box>
    </Fragment>
  )
}

export default DownloadImages
