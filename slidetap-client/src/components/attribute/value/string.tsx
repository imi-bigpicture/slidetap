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

import { ExpandLess, ExpandMore } from '@mui/icons-material'
import { Box, TextField } from '@mui/material'
import React from 'react'
import ClearValueAdornment from 'src/components/attribute/value/clear_value_adornment'
import { ItemDetailAction } from 'src/models/action'
import { StringAttributeSchema } from 'src/models/schema/attribute_schema'

interface DisplayStringValueProps {
  value: string | null
  schema: StringAttributeSchema
  action: ItemDetailAction
  handleValueUpdate: (value: string | null) => void
  /** Fill the height available rather than growing to the text. */
  fillHeight?: boolean
  /** Folds the field away. Given here rather than as a header above the field,
   * so the name is not written twice. */
  collapse?: { open: boolean; onToggle: () => void }
}

export default function DisplayStringValue({
  value,
  schema,
  action,
  handleValueUpdate,
  fillHeight = false,
  collapse,
}: DisplayStringValueProps): React.ReactElement {
  const readOnly = action === ItemDetailAction.VIEW || schema.readOnly
  const validValue = value !== null && value !== ''
  const nullIsOk = schema.optional && value === null
  const collapsed = collapse !== undefined && !collapse.open
  const inputRef = React.useRef<HTMLTextAreaElement>(null)
  React.useEffect(() => {
    if (collapse?.open !== true || inputRef.current === null) return
    // Folding keeps the field mounted, so it also keeps how far it was
    // scrolled. Opening it again should show the start of the text, not
    // wherever the reader happened to leave off last time.
    inputRef.current.scrollTop = 0
    // Opening a field picks it out, which is what focus already means for a
    // text field: blue while it is the one being read whether or not the
    // pointer is on it, and handed over when another field is picked. The
    // click on the label cannot do this itself — the input is still hidden at
    // the point the browser acts on it.
    inputRef.current.focus({ preventScroll: true })
  }, [collapse?.open])
  return (
    <TextField
      inputRef={inputRef}
      label={
        collapse === undefined ? (
          schema.displayName
        ) : (
          <Box
            component="span"
            onClick={collapse.onToggle}
            sx={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 0.25,
              cursor: 'pointer',
            }}
          >
            {collapse.open ? (
              <ExpandLess fontSize="inherit" />
            ) : (
              <ExpandMore fontSize="inherit" />
            )}
            {schema.displayName}
          </Box>
        )
      }
      required={!schema.optional}
      value={value ?? ''}
      onChange={(event) => {
        handleValueUpdate(event.target.value)
      }}
      size="small"
      slotProps={{
        input: {
          readOnly: readOnly,
          endAdornment: (
            <ClearValueAdornment
              show={!readOnly && !collapsed && value !== null && value !== ''}
              onClear={() => handleValueUpdate(null)}
              alignTop={schema.multiline}
            />
          ),
        },
        inputLabel: {
          shrink: true,
        },
      }}
      fullWidth
      multiline={schema.multiline}
      // Filling: take the height the parent gives and scroll within it, rather
      // than growing to the text. Not filling: cap it, so a report that runs to
      // hundreds of lines does not push everything below it off the panel.
      maxRows={schema.multiline && !fillHeight ? 12 : undefined}
      sx={{
        // Folded away, the field keeps its name and loses everything else: the
        // box closes right up, leaving the name sitting on a single rule. The
        // grid it sits in already spaces it from the next field, so it adds no
        // margin of its own — closed or open, it takes the same room.
        ...(collapsed && {
          // Closed up, the input box is too thin to hover, so the rule would
          // never darken the way an open field's border does. Hovering
          // anywhere on the field — its name included — counts instead.
          '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: 'text.primary' },
          '& .MuiInputBase-root': { minHeight: 0, height: 0, py: 0 },
          '& .MuiInputBase-input': { display: 'none' },
          // The top edge is the one the outline notches for the label, so that
          // is the edge kept: the rule breaks around the name as it does on an
          // open field, instead of running through it.
          '& .MuiOutlinedInput-notchedOutline': {
            borderBottom: 0,
            borderLeft: 0,
            borderRight: 0,
            borderRadius: 0,
          },
        }),
        ...(fillHeight &&
          !collapsed && {
            // Fills what it is given, which is already no more than its text
            // needs: the wrapper handing out the height clamps itself to
            // max-content, so a short text never sits in a tall box.
            height: '100%',
            '& .MuiInputBase-root': {
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'stretch',
              overflow: 'hidden',
            },
            // The outline is a sibling of the text inside this root, so
            // scrolling the root drags the border up with the text. The
            // textarea scrolls instead, leaving the border where it is. Sized
            // by flex rather than a forced height, so the field still reports
            // how tall its text is to whatever is handing out the height.
            '& .MuiInputBase-input': {
              flex: '1 1 auto',
              minHeight: 0,
              overflow: 'auto !important',
            },
          }),
      }}
      error={!validValue && !nullIsOk}
    />
  )
}
