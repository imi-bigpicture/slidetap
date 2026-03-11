import { Button, DialogActions, DialogContent } from '@mui/material'
import Dialog from '@mui/material/Dialog'
import DialogTitle from '@mui/material/DialogTitle'
import React, { type ReactElement } from 'react'
import type { Image } from 'src/models/item'
import { ItemSelect } from 'src/models/item_select'
import { OpenSeaDragonViewer } from './openseadragonviewer'

interface ImageViewerDialogProps {
  open: boolean
  image: Image
  setOpen: React.Dispatch<React.SetStateAction<boolean>>
  setIncluded?: (image: Image, value: ItemSelect) => void
}

export function ImageViewerDialog({
  image,
  setOpen,
  open,
  setIncluded,
}: ImageViewerDialogProps): ReactElement {
  const handleClose = (): void => {
    setOpen(false)
  }
  const handleExclude = (): void => {
    if (setIncluded === undefined) {
      return
    }
    setIncluded(image, {
      select: false,
      comment: null,
      tags: null,
      additiveTags: false,
    })
    setOpen(false)
  }
  const handleInclude = (): void => {
    if (setIncluded === undefined) {
      return
    }
    setIncluded(image, { select: true, comment: null, tags: null, additiveTags: false })
    setOpen(false)
  }

  return (
    <React.Fragment>
      <Dialog onClose={handleClose} open={open} fullScreen={true}>
        <DialogTitle>Image viewer</DialogTitle>

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
