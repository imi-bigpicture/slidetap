import React from 'react'
import { FormControl, FormLabel, Stack, TextField } from '@mui/material'
import type { NumericAttribute } from 'models/attribute'

interface DisplayNumericAttributeProps {
  attribute: NumericAttribute
}

export default function DisplayNumericAttribute({
  attribute,
}: DisplayNumericAttributeProps): React.ReactElement {
  return (
    <Stack spacing={2} direction="row" sx={{ margin: 2 }}>
      <TextField label="Value" value={attribute.value} />
    </Stack>
  )
}
