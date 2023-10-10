import React from 'react'
import { FormControl, FormLabel, Stack, TextField } from '@mui/material'
import type { DatetimeAttribute } from 'models/attribute'

interface DisplayDatetimeAttributeProps {
  attribute: DatetimeAttribute
  hideLabel?: boolean | undefined
}

export default function DisplayDatetimeAttribute({
  attribute,
  hideLabel,
}: DisplayDatetimeAttributeProps): React.ReactElement {
  return (
    <React.Fragment>
      <FormControl component="fieldset" variant="standard">
        {hideLabel !== true && (
          <FormLabel component="legend">{attribute.schema.displayName}</FormLabel>
        )}
        <Stack spacing={2} direction="row" sx={{ margin: 2 }}>
          <TextField value={attribute.value} />
        </Stack>
      </FormControl>
    </React.Fragment>
  )
}
