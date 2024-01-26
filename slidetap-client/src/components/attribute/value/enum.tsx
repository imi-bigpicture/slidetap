import { MenuItem, Select, Stack } from '@mui/material'
import { Action } from 'models/action'
import type { EnumAttributeSchema } from 'models/schema'
import React from 'react'

interface DisplayEnumValueProps {
  value?: string
  schema: EnumAttributeSchema
  action: Action
  handleValueUpdate: (value: string) => void
}

export default function DisplayEnumValue({
  value,
  schema,
  action,
  handleValueUpdate,
}: DisplayEnumValueProps): React.ReactElement {
  const readOnly = action === Action.VIEW || schema.readOnly
  return (
    <Stack spacing={2} direction="row" sx={{ margin: 2 }}>
      <Select
        value={value}
        onChange={(event) => {
          handleValueUpdate(event.target.value)
        }}
        size="small"
        readOnly={readOnly}
      >
        {schema.allowedValues.map((allowedValue) => (
          <MenuItem key={allowedValue} value={allowedValue}>
            {allowedValue}
          </MenuItem>
        ))}
      </Select>
    </Stack>
  )
}
