import React from 'react'
import { Stack, TextField } from '@mui/material'
import type { NumericAttribute } from 'models/attribute'
import { Action } from 'models/table_item'

interface DisplayNumericAttributeProps {
  attribute: NumericAttribute
  action: Action
  handleAttributeUpdate?: (attribute: NumericAttribute) => void
}

export default function DisplayNumericAttribute({
  attribute,
  action,
  handleAttributeUpdate,
}: DisplayNumericAttributeProps): React.ReactElement {
  const readOnly = action === Action.VIEW

  const handleNumericChange = (value: string): void => {
    attribute.value = parseFloat(value)
    handleAttributeUpdate?.(attribute)
  }
  return (
    <Stack spacing={2} direction="row" sx={{ margin: 2 }}>
      <TextField
        label="Value"
        value={attribute.value}
        onChange={(event) => {
          handleNumericChange(event.target.value)
        }}
        type="number"
        InputProps={{ readOnly }}
      />
    </Stack>
  )
}
