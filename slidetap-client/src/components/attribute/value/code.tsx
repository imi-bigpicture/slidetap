import React from 'react'
import { Stack, TextField } from '@mui/material'
import type { CodeAttribute } from 'models/attribute'

interface DisplayCodeAttributeProps {
  attribute: CodeAttribute
}

export default function DisplayCodeAttribute({
  attribute,
}: DisplayCodeAttributeProps): React.ReactElement {
  return (
    <Stack spacing={1} direction="row" sx={{ margin: 2 }}>
      <TextField label="Code" value={attribute.value?.code} />
      <TextField label="Scheme" value={attribute.value?.scheme} />
      <TextField label="Meaning" value={attribute.value?.meaning} />
    </Stack>
  )
}
