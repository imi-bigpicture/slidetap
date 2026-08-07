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

import { Cancel, OutlinedFlag } from '@mui/icons-material'
import {
  Button,
  FormControl,
  Paper,
  Popover,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import { useState, type ReactElement } from 'react'

interface ReviewFlagPopoverProps {
  /** Where to open, in viewport coordinates. Open while this is set.
   *
   * A position rather than an element: the button that opens this sits inside
   * the identifier hover panel, which unmounts as soon as the pointer leaves
   * it. An anchor element that has left the document leaves MUI nothing to
   * measure, and the popover jumps to the corner of the window. */
  anchorPosition: { top: number; left: number } | null
  /** How many items the flag will be raised on, so a bulk flag says so before
   * it is confirmed. */
  count: number
  onConfirm: (reason: string | null) => void
  onClose: () => void
}

/**
 * Asks why review is wanted before raising a flag, the same way deleting asks
 * for a comment.
 *
 * The reason is what a reviewer reads to know what they were called for, and
 * a flag raised without one gives them nothing to go on — an import at least
 * says which items were invalid. It is still optional: an item flagged while
 * looking straight at it often needs no explanation.
 *
 * Mount it only while open: the reason starts empty each time.
 */
export default function ReviewFlagPopover({
  anchorPosition,
  count,
  onConfirm,
  onClose,
}: ReviewFlagPopoverProps): ReactElement {
  const [reason, setReason] = useState('')

  return (
    <Popover
      open={anchorPosition !== null}
      anchorReference="anchorPosition"
      anchorPosition={anchorPosition ?? undefined}
      onClose={onClose}
      transformOrigin={{ vertical: -10, horizontal: 'center' }}
    >
      <Paper sx={{ p: 2, borderRadius: 2, maxWidth: 300 }}>
        <FormControl component="fieldset" variant="standard">
          <Stack spacing={1} direction="column">
            <Typography variant="body2" color="text.secondary">
              {count === 1
                ? 'Flag this item for review'
                : `Flag ${count} items for review`}
            </Typography>
            <TextField
              label="Reason"
              size="small"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              multiline
              maxRows={4}
              autoFocus
              fullWidth
            />
          </Stack>
        </FormControl>
        <Stack direction="row" spacing={1} sx={{ mt: 2, justifyContent: 'center' }}>
          <Button onClick={() => onConfirm(reason === '' ? null : reason)}>
            <OutlinedFlag />
          </Button>
          <Button onClick={onClose}>
            <Cancel />
          </Button>
        </Stack>
      </Paper>
    </Popover>
  )
}
