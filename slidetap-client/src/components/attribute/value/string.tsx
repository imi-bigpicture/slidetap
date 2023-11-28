import React from 'react'
import { Stack, TextField } from '@mui/material'
import type { StringAttribute } from 'models/attribute'

interface DisplayStringAttributeProps {
  attribute: StringAttribute
  handleAttributeUpdate?: (attribute: StringAttribute) => void
}

export default function DisplayStringAttribute({
  attribute,
  handleAttributeUpdate,
}: DisplayStringAttributeProps): React.ReactElement {
  const readOnly = handleAttributeUpdate === undefined
  const handleStringChange = (value: string): void => {
    attribute.value = value
    handleAttributeUpdate?.(attribute)
  }
  return (
    <Stack spacing={2} direction="row" sx={{ margin: 2 }}>
      <TextField
        value={attribute.value}
        onChange={(event) => {
          handleStringChange(event.target.value)
        }}
        InputProps={{ readOnly }}
      />
    </Stack>
  )
}
