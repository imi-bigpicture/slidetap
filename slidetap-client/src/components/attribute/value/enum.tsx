import React from 'react'
import { Stack, Select, MenuItem } from '@mui/material'
import type { EnumAttribute } from 'models/attribute'

interface DisplayEnumAttributeProps {
  attribute: EnumAttribute
}

export default function DisplayEnumAttribute({
  attribute,
}: DisplayEnumAttributeProps): React.ReactElement {
  return (
    <Stack spacing={2} direction="row" sx={{ margin: 2 }}>
      <Select value={attribute.value}>
        {attribute.schema.allowedValues.map((allowedValue) => (
          <MenuItem key={allowedValue} value={allowedValue}>
            {allowedValue}
          </MenuItem>
        ))}
      </Select>
    </Stack>
  )
}
