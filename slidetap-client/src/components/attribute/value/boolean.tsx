import { Checkbox, FormControlLabel, Radio, RadioGroup, Stack } from '@mui/material'
import { Action } from 'models/action'
import type { BooleanAttribute } from 'models/attribute'
import React from 'react'

interface DisplayBooleanAttributeProps {
  attribute: BooleanAttribute
  action: Action
  handleAttributeUpdate?: (attribute: BooleanAttribute) => void
}

export default function DisplayBooleanAttribute({
  attribute,
  action,
  handleAttributeUpdate,
}: DisplayBooleanAttributeProps): React.ReactElement {
  const readOnly = action === Action.VIEW || attribute.schema.readOnly
  const handleBooleanChange = (value: string): void => {
    attribute.value = value === 'true'
    handleAttributeUpdate?.(attribute)
  }
  return (
    <Stack spacing={2} direction="row" sx={{ margin: 2 }}>
      <RadioGroup
        value={attribute.value}
        onChange={(event) => {
          handleBooleanChange(event.target.value)
        }}
      >
        <Stack direction="row" spacing={2}>
          <FormControlLabel
            value="true"
            control={readOnly ? <Radio readOnly={true} /> : <Checkbox />}
            checked={attribute.value}
            label={attribute.schema.trueDisplayValue}
          />
          <FormControlLabel
            value="false"
            control={readOnly ? <Radio readOnly={true} /> : <Checkbox />}
            label={attribute.schema.falseDisplayValue}
            checked={attribute.value === false}
          />
        </Stack>
      </RadioGroup>
    </Stack>
  )
}
