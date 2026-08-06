//    Copyright 2024 SECTRA AB
//
//    Licensed under the Apache License, Version 2.0 (the "License");
//    you may not use this file except in compliance with the License.
//    You may obtain a copy of the License at
//
//        http://www.apache.org/licenses/LICENSE-2.0
//
//    Unless required by applicable law or agreed to in writing, software
//    distributed under the License is distributed on an "AS IS" BASIS,
//    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//    See the License for the specific language governing permissions and
//    limitations under the License.

import { Checkbox, FormControlLabel, Tooltip } from '@mui/material'
import React from 'react'
import { ItemDetailAction } from 'src/models/action'
import { BooleanAttributeSchema } from 'src/models/schema/attribute_schema'

interface DisplayBooleanValueProps {
  value: boolean | null
  schema: BooleanAttributeSchema
  action: ItemDetailAction
  handleValueUpdate: (value: boolean | null) => void
}

/** Unset → true → false → unset. Unset is a value here, not a missing one:
 * the report may simply not say, which is different from saying no. */
const nextValue = (value: boolean | null): boolean | null => {
  if (value === null) {
    return true
  }
  return value ? false : null
}

/**
 * A boolean that can also be unset, as a single checkbox: ticked for true,
 * empty for false, dashed for unset. Clicking steps through them.
 *
 * A pair of labelled radios says the same thing in three times the width, which
 * matters where many of these are read side by side. The three states differ by
 * shape rather than by shade, since the box is what the eye lands on in a grid
 * of these — but the dash is muted, or at full strength it reads as a value
 * rather than as the absence of one.
 */
export default function DisplayBooleanValue({
  value,
  schema,
  action,
  handleValueUpdate,
}: DisplayBooleanValueProps): React.ReactElement {
  const readOnly = action === ItemDetailAction.VIEW || schema.readOnly
  const unset = value === null
  const missing = unset && !schema.optional
  const stateLabel = unset
    ? 'Not set'
    : value
    ? schema.trueDisplayValue
    : schema.falseDisplayValue

  return (
    <Tooltip title={`${schema.displayName}: ${stateLabel}`}>
      <FormControlLabel
        control={
          <Checkbox
            size="small"
            checked={value === true}
            indeterminate={unset}
            disabled={readOnly}
            onChange={() => handleValueUpdate(nextValue(value))}
            sx={{
              // Unpadded, so the 20px icon box matches the label's line box and
              // the two line up on the first line without an eyeballed offset.
              p: 0,
              mr: 0.75,
              // Not the disabled colour: the control stays live, and greying it
              // out would say it cannot be touched.
              ...(unset && {
                '& .MuiSvgIcon-root': { color: 'text.secondary', opacity: 0.7 },
              }),
              ...(missing && { color: 'error.main' }),
            }}
          />
        }
        label={schema.optional ? schema.displayName : `${schema.displayName} *`}
        // Top aligned, so a name that wraps to two lines does not push the box
        // down and out of line with its neighbours.
        sx={{ m: 0, alignItems: 'flex-start' }}
        slotProps={{
          typography: {
            // The name is known even when the value is not, so only a missing
            // required value colours it.
            sx: {
              fontSize: '0.875rem',
              lineHeight: '20px',
              color: missing ? 'error.main' : undefined,
            },
          },
        }}
      />
    </Tooltip>
  )
}
