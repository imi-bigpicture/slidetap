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
import Dialog from '@mui/material/Dialog'
import DialogActions from '@mui/material/DialogActions'
import DialogContent from '@mui/material/DialogContent'
import DialogContentText from '@mui/material/DialogContentText'
import DialogTitle from '@mui/material/DialogTitle'
import Grid from '@mui/material/Grid'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import React, { useState, type ReactElement } from 'react'
import { Batch } from 'src/models/batch'
import { BatchStatus } from 'src/models/batch_status'
import batchApi from 'src/services/api/batch.api'

const FILTER_FILE_EXTENSIONS = '.json, .xls, .xlsx'

interface SearchProps {
  batch: Batch
  nextView: string
  changeView: (to: string) => void
}

function Search({ batch, nextView, changeView }: SearchProps): ReactElement {
  const queryClient = useQueryClient()
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [dialogOpen, setDialogOpen] = React.useState(false)

  const handleFileChange = (e: React.FormEvent<HTMLInputElement>): void => {
    const files = (e.target as HTMLInputElement).files
    if (files == null || files.length === 0) return
    setSelectedFile(files[0])
  }

  const handleSubmit = (): void => {
    if (batch.status !== BatchStatus.INITIALIZED) {
      setDialogOpen(true)
    } else {
      submit()
    }
  }

  const submitMutation = useMutation({
    mutationFn: (data: { batchUid: string; file: File }) => {
      return batchApi.uploadBatchFile(data.batchUid, data.file)
    },
    onSuccess: (updatedBatch) => {
      queryClient.setQueryData(['batch', batch.uid], updatedBatch)
      changeView(nextView)
    },
  })

  function submit(): void {
    if (selectedFile === null) return
    submitMutation.mutate({ batchUid: batch.uid, file: selectedFile })
  }

  function handleDialogCancel(): void {
    setDialogOpen(false)
  }

  function handleDialogConfirm(): void {
    setDialogOpen(false)
    submit()
  }

  function getSelectedFileName(): string {
    if (selectedFile != null) {
      return selectedFile.name
    }
    return ''
  }

  return (
    <Grid container spacing={1} justifyContent="flex-start" alignItems="flex-start">
      {/* <Grid size={{ xs: 12 }}>
        <StepHeader title="Search" description="Parse search document" />
      </Grid> */}
      <Grid size={{ xs: 4 }}>
        <Stack spacing={1}>
          <Stack direction="row" spacing={1}>
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
          <Button onClick={handleSubmit}>Parse</Button>
        </Stack>
      </Grid>
      <Dialog
        open={dialogOpen}
        onClose={handleDialogCancel}
        aria-labelledby="alert-dialog-title"
        aria-describedby="alert-dialog-description"
      >
        <DialogTitle id="alert-dialog-title">Confirm upload</DialogTitle>
        <DialogContent>
          <DialogContentText id="alert-dialog-description">
            Uploading a new search document will remove existing items from the batch.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDialogCancel}>Cancel</Button>
          <Button onClick={handleDialogConfirm} autoFocus>
            Confirm
          </Button>
        </DialogActions>
      </Dialog>
    </Grid>
  )
}

export default Search
