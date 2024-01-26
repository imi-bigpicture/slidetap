import { Stack, TextField } from '@mui/material'
import { Action } from 'models/action'
import type { NumericAttributeSchema } from 'models/schema'
import React from 'react'

interface DisplayNumericValueProps {
  value?: number
  schema: NumericAttributeSchema
  action: Action
  handleValueUpdate: (value: number) => void
}

export default function DisplayNumericValue({
  value,
  schema,
  action,
  handleValueUpdate,
}: DisplayNumericValueProps): React.ReactElement {
  const readOnly = action === Action.VIEW || schema.readOnly

  const handleNumericChange = (updatedValue: string): void => {
    handleValueUpdate(parseFloat(updatedValue))
  }
  return (
    <Stack spacing={2} direction="row" sx={{ margin: 2 }}>
      <TextField
        label="Value"
        value={value}
        onChange={(event) => {
          handleNumericChange(event.target.value)
        }}
        type="number"
        size="small"
        InputProps={{ readOnly, inputMode: 'numeric' }}
        error={value === undefined && !schema.optional}
      />
    </Stack>
  )
}
