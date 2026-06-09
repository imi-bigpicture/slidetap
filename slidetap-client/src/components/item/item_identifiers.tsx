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

import { Chip, FormControl, Stack, TextField } from '@mui/material'
import React from 'react'
import { usePseudonym } from 'src/contexts/pseudonym/pseudonym_context'
import { ItemDetailAction } from 'src/models/action'
import type { Item } from 'src/models/item'
import { getDisplayIdentifier } from 'src/models/pseudonym'

interface DisplayItemIdentifiersProps {
  item: Item
  action: ItemDetailAction
  direction: 'row' | 'column'
  handleIdentifierUpdate: (identifier: string) => void
  handleNameUpdate: (name: string) => void
  handleCommentUpdate: (comment: string) => void
}

export default function DisplayItemIdentifiers({
  item,
  action,
  direction,
  handleIdentifierUpdate,
  handleNameUpdate,
  handleCommentUpdate,
}: DisplayItemIdentifiersProps): React.ReactElement {
  const { pseudonymMode } = usePseudonym()
  const identifierReadOnly = pseudonymMode || action === ItemDetailAction.VIEW
  const nameReadOnly = pseudonymMode || action === ItemDetailAction.VIEW
  return (
    <FormControl component="fieldset" variant="standard">
      <Stack spacing={1} direction="column">
        <Stack spacing={1} direction={direction} alignItems="center">
          <TextField
            label={pseudonymMode ? 'Pseudonym' : 'Identifier'}
            size="small"
            value={getDisplayIdentifier(item, pseudonymMode)}
            onChange={(event) => {
              handleIdentifierUpdate(event.target.value)
            }}
            helperText={
              pseudonymMode && !item.pseudonym ? 'Generated from item ID' : undefined
            }
            slotProps={{
              input: {
                readOnly: identifierReadOnly,
              },
              inputLabel: {
                shrink: true,
              },
            }}
          />
          {!pseudonymMode && (
            <TextField
              label="Name"
              size="small"
              value={item.name ?? ''}
              onChange={(event) => {
                handleNameUpdate(event.target.value)
              }}
              slotProps={{
                input: {
                  readOnly: nameReadOnly,
                },
                inputLabel: {
                  shrink: true,
                },
              }}
            />
          )}
          {!pseudonymMode && (
            <TextField
              label="Pseudonym"
              size="small"
              value={item.pseudonym ?? ''}
              slotProps={{
                input: {
                  readOnly: true,
                },
                inputLabel: {
                  shrink: true,
                },
              }}
            />
          )}
          <Chip
            label="Selected"
            color={!item.selected ? 'warning' : 'success'}
            size="small"
          />
        </Stack>
        <TextField
          label="Comment"
          size="small"
          value={item.comment ?? undefined}
          onChange={(event) => {
            handleCommentUpdate(event.target.value)
          }}
          slotProps={{
            input: {
              readOnly: action === ItemDetailAction.VIEW,
            },
            inputLabel: {
              shrink: true,
            },
          }}
        />
      </Stack>
    </FormControl>
  )
}
