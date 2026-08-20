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

import ClearIcon from '@mui/icons-material/Clear'
import { IconButton, InputAdornment, Tooltip } from '@mui/material'
import React from 'react'

interface ClearValueAdornmentProps {
  /** Whether the field holds anything to clear. */
  show: boolean
  /** Clears the field, refusing what the item came in with. */
  onClear: () => void
  /** Sit at the first line rather than halfway down, for a field that grows to
   * its text. */
  alignTop?: boolean
  /** Leave room for the arrow a select draws over its right edge. */
  insetEnd?: boolean
}

/** The way to empty a field, next to the value it empties.
 *
 * Emptying a text field by hand only leaves it blank for as long as the edit
 * stands; this says the field is meant to be empty, and the imported value is
 * refused rather than left to fill it back in.
 */
export default function ClearValueAdornment({
  show,
  onClear,
  alignTop = false,
  insetEnd = false,
}: ClearValueAdornmentProps): React.ReactElement | null {
  if (!show) {
    return null
  }
  return (
    <InputAdornment
      position="end"
      sx={{
        ...(alignTop && { alignSelf: 'flex-start', mt: 1 }),
        ...(insetEnd && { mr: 2 }),
      }}
    >
      <Tooltip title="Clear value">
        <IconButton
          aria-label="Clear value"
          size="small"
          edge="end"
          // Not a stop on the way through the form: tabbing goes from field to
          // field, and this is reached by pointer.
          tabIndex={-1}
          // A select opens its list on any press within the field, this one
          // included.
          onMouseDown={(event) => event.stopPropagation()}
          onClick={(event) => {
            event.stopPropagation()
            onClear()
          }}
        >
          <ClearIcon fontSize="small" />
        </IconButton>
      </Tooltip>
    </InputAdornment>
  )
}
