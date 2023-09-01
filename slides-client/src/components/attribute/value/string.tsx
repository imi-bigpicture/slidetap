import React from 'react'
import { FormControl, FormLabel, Stack, TextField } from '@mui/material'
import { StringAttribute } from 'models/attribute'

interface DisplayStringAttributeProps {
    attribute: StringAttribute
    hideLabel?: boolean | undefined
}

export default function DisplayStringAttribute (
    { attribute, hideLabel }: DisplayStringAttributeProps
): React.ReactElement {
    return (
        <React.Fragment>
            <FormControl component="fieldset" variant="standard">
                {hideLabel !== true && <FormLabel component="legend">{attribute.schemaDisplayName}</FormLabel>}
                <Stack spacing={2} direction="row" sx={{ margin: 2 }}>
                    <TextField
                        value={attribute.value}
                    />
                </Stack>
            </FormControl>
        </React.Fragment>
    )
}
