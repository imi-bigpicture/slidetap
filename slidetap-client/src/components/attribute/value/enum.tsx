import React from 'react'
import { Stack, Select, MenuItem } from '@mui/material'
import type { EnumAttribute } from 'models/attribute'

interface DisplayEnumAttributeProps {
  attribute: EnumAttribute
  handleAttributeUpdate?: (attribute: EnumAttribute) => void
}

export default function DisplayEnumAttribute({
  attribute,
  handleAttributeUpdate,
}: DisplayEnumAttributeProps): React.ReactElement {
  const readOnly = handleAttributeUpdate === undefined
  const handleEnumChange = (value: string): void => {
    attribute.value = value
    handleAttributeUpdate?.(attribute)
  }
  return (
    <Stack spacing={2} direction="row" sx={{ margin: 2 }}>
      <Select
        value={attribute.value}
        onChange={(event) => {
          handleEnumChange(event.target.value)
        }}
        readOnly={readOnly}
      >
        {attribute.schema.allowedValues.map((allowedValue) => (
          <MenuItem key={allowedValue} value={allowedValue}>
            {allowedValue}
          </MenuItem>
        ))}
      </Select>
    </Stack>
  )
}
