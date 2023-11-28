import React from 'react'
import { Stack, RadioGroup, FormControlLabel, Radio } from '@mui/material'
import type { BooleanAttribute } from 'models/attribute'

interface DisplayBooleanAttributeProps {
  attribute: BooleanAttribute
}

export default function DisplayBooleanAttribute({
  attribute,
}: DisplayBooleanAttributeProps): React.ReactElement {
  return (
    <Stack spacing={2} direction="row" sx={{ margin: 2 }}>
      <RadioGroup value={attribute.value}>
        <FormControlLabel
          value="true"
          control={<Radio />}
          label={attribute.schema.trueDisplayValue}
        />
        <FormControlLabel
          value="false"
          control={<Radio />}
          label={attribute.schema.falseDisplayValue}
        />
      </RadioGroup>
    </Stack>
  )
}
