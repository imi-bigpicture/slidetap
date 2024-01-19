import { MenuItem, Select, Stack } from '@mui/material'
import { Action } from 'models/action'
import type { EnumAttribute } from 'models/attribute'
import React from 'react'

interface DisplayEnumAttributeProps {
  attribute: EnumAttribute
  action: Action
  handleAttributeUpdate?: (attribute: EnumAttribute) => void
}

export default function DisplayEnumAttribute({
  attribute,
  action,
  handleAttributeUpdate,
}: DisplayEnumAttributeProps): React.ReactElement {
  const readOnly = action === Action.VIEW || attribute.schema.readOnly
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
