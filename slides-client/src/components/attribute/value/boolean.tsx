import React from 'react'
import { FormControl, FormLabel, Stack, RadioGroup, FormControlLabel, Radio } from '@mui/material'
import type { BooleanAttribute } from 'models/attribute'

interface DisplayBooleanAttributeProps {
  attribute: BooleanAttribute
  hideLabel?: boolean | undefined
}

export default function DisplayBooleanAttribute({
  attribute,
  hideLabel,
}: DisplayBooleanAttributeProps): React.ReactElement {
    return (
        <React.Fragment>
            <FormControl component="fieldset" variant="standard">
            {hideLabel !== true && (
                <FormLabel component="legend">{attribute.schema.displayName}</FormLabel>
            )}
                <Stack spacing={2} direction="row" sx={{ margin: 2 }}>
                <RadioGroup
                    aria-labelledby="demo-controlled-radio-buttons-group"
                    name="controlled-radio-buttons-group"
                    value={attribute.value}
                >
                    <FormControlLabel value="true" control={<Radio />} label={attribute.schema.trueDisplayValue} />
                    <FormControlLabel value="false" control={<Radio />} label={attribute.schema.falseDispalyValue} />
                </RadioGroup>
            </Stack>
        </FormControl>
    </React.Fragment>
  )
}
