import { Stack, TextField } from '@mui/material'
import { Action } from 'models/action'
import type { Measurement } from 'models/attribute'
import type { MeasurementAttributeSchema } from 'models/schema'
import React from 'react'

interface DisplayMeasurementValueProps {
  value?: Measurement
  schema: MeasurementAttributeSchema
  action: Action
  handleValueUpdate: (value: Measurement) => void
}

export default function DisplayMeasurementValue({
  value,
  schema,
  action,
  handleValueUpdate,
}: DisplayMeasurementValueProps): React.ReactElement {
  const readOnly = action === Action.VIEW || schema.readOnly
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
        label="Value"
        value={value?.value}
        onChange={(event) => {
          handleMeasurementChange('value', event.target.value)
        }}
        type="number"
        size="small"
        InputProps={{ readOnly }}
        error={value?.value === undefined && !schema.optional}
      />
      <TextField
        label="Unit"
        value={value?.unit}
        onChange={(event) => {
          handleMeasurementChange('unit', event.target.value)
        }}
        size="small"
        InputProps={{ readOnly }}
        error={(value?.unit === undefined || value.unit === '') && !schema.optional}
      />
    </Stack>
  )
}
