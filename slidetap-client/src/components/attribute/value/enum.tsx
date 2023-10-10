import React from 'react'
import { FormControl, FormLabel, Stack, Select, MenuItem } from '@mui/material'
import type { EnumAttribute } from 'models/attribute'

interface DisplayEnumAttributeProps {
  attribute: EnumAttribute
  hideLabel?: boolean | undefined
}

export default function DisplayEnumAttribute({
  attribute,
  hideLabel,
}: DisplayEnumAttributeProps): React.ReactElement {
    return (
        <React.Fragment>
            <FormControl component="fieldset" variant="standard">
            {hideLabel !== true && (
                <FormLabel component="legend">{attribute.schema.displayName}</FormLabel>
            )}
            <Stack spacing={2} direction="row" sx={{ margin: 2 }}>
                <Select
                    value={attribute.value}
                    >
                        {attribute.schema.allowedValues.map((allowedValue) =>
                        (
                            <MenuItem
                            key={allowedValue}
                            value={allowedValue}
                        >{allowedValue}
                            </MenuItem>
                        ))}
                </Select>
            </Stack>
        </FormControl>
    </React.Fragment>
  )
}
