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

import { Button, DialogActions, DialogContent } from '@mui/material'
import Dialog from '@mui/material/Dialog'
import DialogTitle from '@mui/material/DialogTitle'
import type { Image } from 'models/item'
import React, { type ReactElement } from 'react'
import { OpenSeaDragonViewer } from './openseadragonviewer'

interface ValidateImageProps {
  open: boolean
  image: Image
  setOpen: React.Dispatch<React.SetStateAction<boolean>>
  setIncluded?: (image: Image, include: boolean) => void
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
