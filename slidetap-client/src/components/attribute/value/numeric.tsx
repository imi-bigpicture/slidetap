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
import ClearValueAdornment from 'src/components/attribute/value/clear_value_adornment'
import { ItemDetailAction } from 'src/models/action'
import { useTypedText } from './use_typed_text'
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
  /** Emptied means emptied, not the nothing that `parseFloat` makes of an
   * empty field, which is the same nothing a half-written number makes. */
  const typed = useTypedText(value === null ? '' : String(value), (written) => {
    const trimmed = written.trim()
    handleValueUpdate(trimmed === '' ? null : Number(trimmed))
  })
  const written = typed.text.trim() === '' ? null : Number(typed.text)
  const validValue =
    written !== null &&
    !isNaN(written) &&
    (schema.minValue === null || written >= schema.minValue) &&
    (schema.maxValue === null || written <= schema.maxValue)
  const nullIsOk = schema.optional && typed.text.trim() === ''
  return (
    <TextField
      label={schema.displayName}
      required={!schema.optional}
      value={typed.text}
      onChange={(event) => {
        typed.onChange(event.target.value)
      }}
      onBlur={typed.onBlur}
      type="number"
      size="small"
      slotProps={{
        input: {
          readOnly: readOnly,
          inputMode: 'numeric',
          endAdornment: (
            <ClearValueAdornment
              show={!readOnly && typed.text !== ''}
              onClear={() => handleValueUpdate(null)}
            />
          ),
        },
        inputLabel: {
          shrink: true,
        },
        htmlInput: {
          min: schema.minValue,
          max: schema.maxValue,
          step: schema.isInteger ? 1 : 'any',
        },
      }}
      fullWidth
      error={!validValue && !nullIsOk}
    />
  )
}
