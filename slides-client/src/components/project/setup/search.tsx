import React, { useState, ReactElement, Fragment } from 'react'
import Button from '@mui/material/Button'
import projectApi from 'services/api/project_api'
import { Stack, TextField } from '@mui/material'
import { Box } from '@mui/system'
import { Project } from 'models/project'
import Dialog from '@mui/material/Dialog'
import DialogActions from '@mui/material/DialogActions'
import DialogContent from '@mui/material/DialogContent'
import DialogContentText from '@mui/material/DialogContentText'
import DialogTitle from '@mui/material/DialogTitle'
import StepHeader from 'components/step_header'
import { ProjectStatus } from 'models/status'

// const FILTER_FILE_EXTENSIONS = '.xls, .xlsx'
const FILTER_FILE_EXTENSIONS = '.json'

interface SearchProps {
  project: Project
  nextView: string
  changeView: (to: string) => void
}

function Search({ project, nextView, changeView }: SearchProps): ReactElement {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [dialogOpen, setDialogOpen] = React.useState(false)

  const handleFileChange = (e: React.FormEvent<HTMLInputElement>): void => {
    const files = (e.target as HTMLInputElement).files
    if (files == null || files.length === 0) return
    setSelectedFile(files[0])
  }

  const handleSubmitProject = (e: React.MouseEvent<HTMLElement>): void => {
    if (project.status !== ProjectStatus.NOT_STARTED) {
      setDialogOpen(true)
    } else {
      submitProject()
    }
  }

  function submitProject(): void {
    if (selectedFile === null || project.uid === undefined) return
    projectApi
      .uploadProjectFile(project.uid, selectedFile)
      .catch((x) => console.error('Failed to upload project file', x))
    changeView(nextView)
  }

  function handleDialogCancel(): void {
    setDialogOpen(false)
  }

  function handleDialogConfirm(): void {
    setDialogOpen(false)
    submitProject()
  }

  function getSelectedFileName(): string {
    if (selectedFile != null) {
      return selectedFile.name
    }
    return ''
  }

  return (
    <Fragment>
      <StepHeader title="Search" description="Parse search document" />
      <br />
      <Box sx={{ width: 300 }}>
        <Stack spacing={2}>
          <Stack direction="row" spacing={2}>
            <TextField
              id="fileName"
              label="Filename"
              variant="standard"
              value={getSelectedFileName()}
              autoFocus
            />
            <Button component="label">
              Browse
              <input
                type="file"
                hidden
                accept={FILTER_FILE_EXTENSIONS}
                onChange={handleFileChange}
              />
            </Button>
          </Stack>
          <Button onClick={handleSubmitProject}>Parse</Button>
        </Stack>
      </Box>
      <Dialog
        open={dialogOpen}
        onClose={handleDialogCancel}
        aria-labelledby="alert-dialog-title"
        aria-describedby="alert-dialog-description"
      >
        <DialogTitle id="alert-dialog-title">Confirm upload</DialogTitle>
        <DialogContent>
          <DialogContentText id="alert-dialog-description">
            Uploading a new search document will remove existing items from project.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDialogCancel}>Cancel</Button>
          <Button onClick={handleDialogConfirm} autoFocus>
            Confirm
          </Button>
        </DialogActions>
      </Dialog>
    </Fragment>
  )
}

export default Search
