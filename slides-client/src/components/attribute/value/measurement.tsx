import React from 'react'
import { FormControl, FormLabel, Stack, TextField } from '@mui/material'
import { MeasurementAttribute } from 'models/attribute'

interface DisplayMeasurementAttributeProps {
  attribute: MeasurementAttribute
  hideLabel?: boolean | undefined
}

export default function DisplayMeasurementAttribute({
  attribute,
  hideLabel,
}: DisplayMeasurementAttributeProps): React.ReactElement {
  return (
    <React.Fragment>
      <FormControl component="fieldset" variant="standard">
        {hideLabel !== true && (
          <FormLabel component="legend">{attribute.schemaDisplayName}</FormLabel>
        )}
        <Stack spacing={2} direction="row" sx={{ margin: 2 }}>
          <TextField label="Value" value={attribute.value} />
          <TextField label="Unit" value={attribute.unit} />
        </Stack>
      </FormControl>
    </React.Fragment>
  )
}
