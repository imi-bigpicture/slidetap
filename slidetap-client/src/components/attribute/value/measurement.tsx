import { Stack, TextField } from '@mui/material'
import type { MeasurementAttribute } from 'models/attribute'
import { Action } from 'models/table_item'
import React from 'react'

interface DisplayMeasurementAttributeProps {
  attribute: MeasurementAttribute
  action: Action
  handleAttributeUpdate?: (attribute: MeasurementAttribute) => void
}

export default function DisplayMeasurementAttribute({
  attribute,
  action,
  handleAttributeUpdate,
}: DisplayMeasurementAttributeProps): React.ReactElement {
  const readOnly = action === Action.VIEW || attribute.schema.readOnly
  const handleMeasurementChange = (attr: 'value' | 'unit', value: string): void => {
    if (attr === 'value') {
      attribute.value = {
        value: parseFloat(value),
        unit: attribute.value !== undefined ? attribute.value.unit : '',
      }
    } else if (attr === 'unit' && typeof value === 'string') {
      attribute.value = {
        value: attribute.value !== undefined ? attribute.value.value : 0,
        unit: value,
      }
    }
    handleAttributeUpdate?.(attribute)
  }
  return (
    <Stack spacing={2} direction="row" sx={{ margin: 2 }}>
      <TextField
        label="Value"
        value={attribute.value?.value}
        onChange={(event) => {
          handleMeasurementChange('value', event.target.value)
        }}
        type="number"
        InputProps={{ readOnly }}
        error={attribute.value?.value === undefined && !attribute.schema.optional}
      />
      <TextField
        label="Unit"
        value={attribute.value?.unit}
        onChange={(event) => {
          handleMeasurementChange('unit', event.target.value)
        }}
        InputProps={{ readOnly }}
        error={attribute.value?.unit === undefined && !attribute.schema.optional}
      />
    </Stack>
  )
}
