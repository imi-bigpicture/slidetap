import React from 'react'
import { Stack, TextField } from '@mui/material'
import type { StringAttribute } from 'models/attribute'

interface DisplayStringAttributeProps {
  attribute: StringAttribute
}

export default function DisplayStringAttribute({
  attribute,
}: DisplayStringAttributeProps): React.ReactElement {
  return (
    <Stack spacing={2} direction="row" sx={{ margin: 2 }}>
      <TextField value={attribute.value} />
    </Stack>
  )
}
