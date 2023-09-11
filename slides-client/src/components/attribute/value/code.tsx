import React from 'react'
import { FormControl, FormLabel, Stack, TextField } from '@mui/material'
import type { CodeAttribute } from 'models/attribute'

interface DisplayCodeAttributeProps {
  attribute: CodeAttribute
  hideLabel?: boolean | undefined
}

export default function DisplayCodeAttribute({
  attribute,
  hideLabel,
}: DisplayCodeAttributeProps): React.ReactElement {
  return (
    <React.Fragment>
      <FormControl component="fieldset" variant="standard">
        {hideLabel !== true && (
          <FormLabel component="legend">{}</FormLabel>
        )}
        <Stack spacing={2} direction="row" sx={{ margin: 2 }}>
          <TextField label="Code" value={attribute.value?.code} />
          <TextField label="Scheme" value={attribute.value?.scheme} />
          <TextField label="Meaning" value={attribute.value?.meaning} />
        </Stack>
      </FormControl>
    </React.Fragment>
  )
}
