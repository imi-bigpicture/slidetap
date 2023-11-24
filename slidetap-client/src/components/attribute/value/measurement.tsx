import React from 'react'
import { Stack, TextField } from '@mui/material'
import type { MeasurementAttribute } from 'models/attribute'

interface DisplayMeasurementAttributeProps {
  attribute: MeasurementAttribute
}

export default function DisplayMeasurementAttribute({
  attribute,
}: DisplayMeasurementAttributeProps): React.ReactElement {
  return (
    <Stack spacing={2} direction="row" sx={{ margin: 2 }}>
      <TextField label="Value" value={attribute.value?.value} />
      <TextField label="Unit" value={attribute.value?.unit} />
    </Stack>
  )
}
