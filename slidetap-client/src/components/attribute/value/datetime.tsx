import { Stack, TextField } from '@mui/material'
import { Action } from 'models/action'
import type { DatetimeAttributeSchema } from 'models/schema'
import React from 'react'

interface DisplayDatetimeValueProps {
  value?: Date
  schema: DatetimeAttributeSchema
  action: Action
  handleValueUpdate: (value: Date) => void
}

export default function DisplayDatetimeValue({
  value,
  schema,
  action,
  handleValueUpdate,
}: DisplayDatetimeValueProps): React.ReactElement {
  const readOnly = action === Action.VIEW || schema.readOnly
  const handleDatetimeChange = (updatedValue: string): void => {
    handleValueUpdate(new Date(updatedValue))
  }
  return (
    <Stack spacing={2} direction="row" sx={{ margin: 2 }}>
      <TextField
        value={value}
        onChange={(event) => {
          handleDatetimeChange(event.target.value)
        }}
        size="small"
        InputProps={{ readOnly }}
        error={value === undefined && !schema.optional}
      />
    </Stack>
  )
}
