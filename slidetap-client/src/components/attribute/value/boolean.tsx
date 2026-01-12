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

import { FormControlLabel, Radio, RadioGroup } from '@mui/material'
import React from 'react'
import { ItemDetailAction } from 'src/models/action'
import { BooleanAttributeSchema } from 'src/models/schema/attribute_schema'
import OutlinedFormControl from '../outlined_form_control'

interface DisplayBooleanValueProps {
  value: boolean | null
  schema: BooleanAttributeSchema
  action: ItemDetailAction
  handleValueUpdate: (value: boolean | null) => void
}

export default function DisplayBooleanValue({
  value,
  schema,
  action,
  handleValueUpdate,
}: DisplayBooleanValueProps): React.ReactElement {
  const readOnly = action === ItemDetailAction.VIEW || schema.readOnly
  const handleBooleanChange = (value: string): void => {
    handleValueUpdate(value === 'true')
  }
  const validValue = value !== null
  const nullIsOk = schema.optional && value === null
  return (
    <OutlinedFormControl
      label={schema.displayName}
      required={!schema.optional}
      error={!validValue && !nullIsOk}
      fullWidth
    >
      <RadioGroup
        title={schema.displayName}
        value={value === null ? '' : String(value)}
        row
        onChange={(event) => {
          const newValue = event.target.value
          if (newValue === '') {
            handleValueUpdate(null)
          } else {
            handleBooleanChange(newValue)
          }
        }}
      >
        <FormControlLabel
          value="true"
          control={<Radio size="small" readOnly={readOnly} />}
          label={schema.trueDisplayValue}
          title={schema.trueDisplayValue}
          disabled={readOnly}
          sx={{ m: 0 }}
          slotProps={{ typography: { fontSize: '0.875rem' } }}
        />
        <FormControlLabel
          value="false"
          control={<Radio size="small" readOnly={readOnly} />}
          label={schema.falseDisplayValue}
          title={schema.falseDisplayValue}
          disabled={readOnly}
          sx={{ m: 0 }}
          slotProps={{ typography: { fontSize: '0.875rem' } }}
        />
      </RadioGroup>
    </OutlinedFormControl>
  )
}
