import { Button, DialogActions, DialogContent } from '@mui/material'
import Dialog from '@mui/material/Dialog'
import DialogTitle from '@mui/material/DialogTitle'
import type { ImageDetails } from 'models/item'
import React, { type ReactElement } from 'react'
import { OpenSeaDragonViewer } from './openseadragonviewer'

interface ValidateImageProps {
  open: boolean
  image: ImageDetails
  setOpen: React.Dispatch<React.SetStateAction<boolean>>
  setIncluded?: (image: ImageDetails, include: boolean) => void
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
    if (setIncluded === undefined) {
      return
    }
    setIncluded(image, false)
    setOpen(false)
  }
  const handleInclude = (): void => {
    if (setIncluded === undefined) {
      return
    }
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
        {setIncluded !== undefined && (
          <DialogActions style={{ justifyContent: 'space-between' }}>
            <Button onClick={handleClose}>Close</Button>
            {image.selected && <Button onClick={handleExclude}>Exclude</Button>}
            {!image.selected && <Button onClick={handleInclude}>Include</Button>}
          </DialogActions>
        )}
      </Dialog>
    </React.Fragment>
  )
}
