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

import { Stack, TextField } from '@mui/material'
import React from 'react'
import { ItemDetailAction } from 'src/models/action'
import { Measurement } from 'src/models/measurement'
import { MeasurementAttributeSchema } from 'src/models/schema/attribute_schema'

interface DisplayMeasurementValueProps {
  value: Measurement | null
  schema: MeasurementAttributeSchema
  action: ItemDetailAction
  handleValueUpdate: (value: Measurement | null) => void
}

export default function DisplayMeasurementValue({
  value,
  schema,
  action,
  handleValueUpdate,
}: DisplayMeasurementValueProps): React.ReactElement {
  const readOnly = action === ItemDetailAction.VIEW || schema.readOnly
  const handleMeasurementChange = (
    attr: 'value' | 'unit',
    updatedValue: string,
  ): void => {
    const updatedMeasurement = {
      value: value?.value ?? 0,
      unit: value?.unit ?? '',
    }
    if (attr === 'value') {
      updatedMeasurement.value = parseFloat(updatedValue)
    } else if (attr === 'unit' && typeof updatedValue === 'string') {
      updatedMeasurement.unit = updatedValue
    }
    handleValueUpdate(updatedMeasurement)
  }
  return (
    <Stack spacing={1} direction="row">
      <TextField
        label={schema.displayName}
        required={!schema.optional}
        value={value?.value}
        onChange={(event) => {
          handleMeasurementChange('value', event.target.value)
        }}
        type="number"
        size="small"
        slotProps={{
          input: {
            readOnly: readOnly,
          },
        }}
        fullWidth
        error={value?.value === null && !schema.optional}
      />
      <TextField
        label="Unit"
        required={!schema.optional}
        value={value?.unit}
        onChange={(event) => {
          handleMeasurementChange('unit', event.target.value)
        }}
        size="small"
        slotProps={{
          input: {
            readOnly: readOnly,
          },
          htmlInput: {
            min: schema.minValue,
            max: schema.maxValue,
          },
        }}
        fullWidth
        error={(value?.unit === null || value?.unit === '') && !schema.optional}
      />
    </Stack>
  )
}
