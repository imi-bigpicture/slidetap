import { FormControl, Stack, TextField } from '@mui/material'
import { Action } from 'models/action'
import type { ItemDetails } from 'models/item'
import React from 'react'

interface DisplayItemIdentifiersProps {
  item: ItemDetails
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
            value={item.name}
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
