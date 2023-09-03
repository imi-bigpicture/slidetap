import React from 'react'
import { FormControl, FormLabel, Stack, TextField } from '@mui/material'
import { NumericAttribute } from 'models/attribute'

interface DisplayNumericAttributeProps {
  attribute: NumericAttribute
  hideLabel?: boolean | undefined
}

export default function DisplayNumericAttribute({
  attribute,
  hideLabel,
}: DisplayNumericAttributeProps): React.ReactElement {
  return (
    <React.Fragment>
      <FormControl component="fieldset" variant="standard">
        {hideLabel !== true && (
          <FormLabel component="legend">{attribute.schemaDisplayName}</FormLabel>
        )}
        <Stack spacing={2} direction="row" sx={{ margin: 2 }}>
          <TextField label="Value" value={attribute.value} />
        </Stack>
      </FormControl>
    </React.Fragment>
  )
}
