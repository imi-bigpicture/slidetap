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

import { FormControl, Stack, TextField } from '@mui/material'
import { Action } from 'models/action'
import type { Item } from 'models/item'
import React from 'react'

interface DisplayItemIdentifiersProps {
  item: Item
  action: Action
  handleIdentifierUpdate: (identifier: string) => void
  handleNameUpdate: (name: string) => void
}

export default function DisplayItemIdentifiers({
  item,
  action,
  handleIdentifierUpdate,
  handleNameUpdate,
}: DisplayItemIdentifiersProps): React.ReactElement {
  return (
    <FormControl component="fieldset" variant="standard">
      <Stack spacing={1} direction="row">
        <TextField
          label="Identifier"
          value={item.identifier}
          onChange={(event) => {
            handleIdentifierUpdate(event.target.value)
          }}
          InputProps={{ readOnly: action === Action.VIEW }}
        />
        {item.name !== undefined && (
          <TextField
            label="Name"
            value={item.name ?? ''}
            onChange={(event) => {
              handleNameUpdate(event.target.value)
            }}
            InputProps={{ readOnly: action === Action.VIEW }}
          />
        )}
        {item.pseodonym !== undefined && (
          <TextField
            label="Pseudonym"
            value={item.pseodonym}
            InputProps={{ readOnly: true }}
          />
        )}
      </Stack>
    </FormControl>
  )
}
