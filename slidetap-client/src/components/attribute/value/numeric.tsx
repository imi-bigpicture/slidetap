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

import { TextField } from '@mui/material'
import React from 'react'
import { ItemDetailAction } from 'src/models/action'
import { NumericAttributeSchema } from 'src/models/schema/attribute_schema'

interface DisplayNumericValueProps {
  value: number | null
  schema: NumericAttributeSchema
  action: ItemDetailAction
  handleValueUpdate: (value: number | null) => void
}

export default function DisplayNumericValue({
  value,
  schema,
  action,
  handleValueUpdate,
}: DisplayNumericValueProps): React.ReactElement {
  const readOnly = action === ItemDetailAction.VIEW || schema.readOnly

  const handleNumericChange = (updatedValue: string): void => {
    handleValueUpdate(parseFloat(updatedValue))
  }
  const validValue =
    value !== null &&
    !isNaN(value) &&
    (schema.minValue === null || value >= schema.minValue) &&
    (schema.maxValue === null || value <= schema.maxValue)
  const nullIsOk = schema.optional && value === null
  return (
    <TextField
      label={schema.displayName}
      required={!schema.optional}
      value={value ?? ''}
      onChange={(event) => {
        handleNumericChange(event.target.value)
      }}
      type="number"
      size="small"
      slotProps={{
        input: {
          readOnly: readOnly,
          inputMode: 'numeric',
        },
        inputLabel: {
          shrink: true,
        },
        htmlInput: {
          min: schema.minValue,
          max: schema.maxValue,
          step: schema.isInt ? 1 : 'any',
        },
      }}
      fullWidth
      error={!validValue && !nullIsOk}
    />
  )
}
