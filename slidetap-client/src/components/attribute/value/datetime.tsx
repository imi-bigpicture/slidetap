import React from 'react'
import { Stack, TextField } from '@mui/material'
import type { DatetimeAttribute } from 'models/attribute'

interface DisplayDatetimeAttributeProps {
  attribute: DatetimeAttribute
}

export default function DisplayDatetimeAttribute({
  attribute,
}: DisplayDatetimeAttributeProps): React.ReactElement {
  return (
    <Stack spacing={2} direction="row" sx={{ margin: 2 }}>
      <TextField value={attribute.value} />
    </Stack>
  )
}
