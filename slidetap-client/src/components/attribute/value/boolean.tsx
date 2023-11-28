import React, { type ReactElement } from 'react'
import { Stack, RadioGroup, FormControlLabel, Radio, Checkbox } from '@mui/material'
import type { BooleanAttribute } from 'models/attribute'

interface DisplayBooleanAttributeProps {
  attribute: BooleanAttribute
  handleAttributeUpdate?: (attribute: BooleanAttribute) => void
}

export default function DisplayBooleanAttribute({
  attribute,
  handleAttributeUpdate,
}: DisplayBooleanAttributeProps): React.ReactElement {
  const readOnly = handleAttributeUpdate === undefined
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
