import React from 'react'
import { Mapping } from 'models/mapper'
import { FormControl, Stack, TextField } from '@mui/material'

interface DisplayMappingProps {
  mapping: Mapping
}

export default function DisplayMapping({
  mapping,
}: DisplayMappingProps): React.ReactElement {
  return (
    <React.Fragment>
      <FormControl component="fieldset" variant="standard">
        <Stack spacing={2} direction="row" sx={{ margin: 2 }}>
          <TextField label="Mappable value" value={mapping.mappableValue} />
          <TextField label="Mapper name" value={mapping.mapperName} />
          <TextField label="Expression" value={mapping.expression} />
        </Stack>
      </FormControl>
    </React.Fragment>
  )
}
