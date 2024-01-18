import { Stack, TextField } from '@mui/material'
import type { DatetimeAttribute } from 'models/attribute'
import { Action } from 'models/table_item'
import React from 'react'

interface DisplayDatetimeAttributeProps {
  attribute: DatetimeAttribute
  action: Action
  handleAttributeUpdate?: (attribute: DatetimeAttribute) => void
}

export default function DisplayDatetimeAttribute({
  attribute,
  action,
  handleAttributeUpdate,
}: DisplayDatetimeAttributeProps): React.ReactElement {
  const readOnly = action === Action.VIEW || attribute.schema.readOnly
  const handleDatetimeChange = (value: string): void => {
    attribute.value = new Date(value)
    handleAttributeUpdate?.(attribute)
  }
  return (
    <Stack spacing={2} direction="row" sx={{ margin: 2 }}>
      <TextField
        value={attribute.value}
        onChange={(event) => {
          handleDatetimeChange(event.target.value)
        }}
        InputProps={{ readOnly }}
        error={attribute.value === undefined && !attribute.schema.optional}
      />
    </Stack>
  )
}
