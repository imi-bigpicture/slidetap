import { Button, DialogActions, DialogContent, Stack, TextField } from '@mui/material'
import Dialog from '@mui/material/Dialog'
import DialogTitle from '@mui/material/DialogTitle'
import React, { ReactElement } from 'react'
import { Image } from 'models/items'
import { OpenSeaDragonViewer } from './openseadragonviewer'

interface ValidateImageProps {
  open: boolean
  image: Image
  setOpen: React.Dispatch<React.SetStateAction<boolean>>
  setIncluded: (image: Image, include: boolean) => void
}

export function ValidateImage({
  image,
  setOpen,
  open,
  setIncluded,
}: ValidateImageProps): ReactElement {
  const handleClose = (): void => {
    setOpen(false)
  }
  const handleExclude = (): void => {
    setIncluded(image, false)
    setOpen(false)
  }
  const handleInclude = (): void => {
    setIncluded(image, true)
    setOpen(false)
  }

  return (
    <React.Fragment>
      <Dialog onClose={handleClose} open={open} fullScreen={true}>
        <DialogTitle>Validate image</DialogTitle>

        <DialogContent>
          <br />
          {open && <OpenSeaDragonViewer imageUid={image.uid} />}
        </DialogContent>
        <DialogActions style={{ justifyContent: 'space-between' }}>
          <Button onClick={handleClose}>Close</Button>
          {image.selected && <Button onClick={handleExclude}>Exclude</Button>}
          {!image.selected && <Button onClick={handleInclude}>Include</Button>}
        </DialogActions>
      </Dialog>
    </React.Fragment>
  )
}
