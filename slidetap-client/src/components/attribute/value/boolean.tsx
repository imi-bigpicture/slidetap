import { FormControlLabel, Radio, RadioGroup } from '@mui/material'
import { Action } from 'models/action'
import type { BooleanAttributeSchema } from 'models/schema'
import React from 'react'

interface DisplayBooleanValueProps {
  value?: boolean
  schema: BooleanAttributeSchema
  action: Action
  handleValueUpdate: (value: boolean) => void
}

export default function DisplayBooleanValue({
  value,
  schema,
  action,
  handleValueUpdate,
}: DisplayBooleanValueProps): React.ReactElement {
  const readOnly = action === Action.VIEW || schema.readOnly
  const handleBooleanChange = (value: string): void => {
    handleValueUpdate(value === 'true')
  }
  return (
    <RadioGroup
      value={value ?? null}
      row
      onChange={(event) => {
        handleBooleanChange(event.target.value)
      }}
    >
      <FormControlLabel
        value={true}
        control={
          readOnly ? <Radio size="small" readOnly={true} er /> : <Radio size="small" />
        }
        label={schema.trueDisplayValue}
      />
      <FormControlLabel
        value={false}
        control={
          readOnly ? <Radio size="small" readOnly={true} /> : <Radio size="small" />
        }
        label={schema.falseDisplayValue}
      />
    </RadioGroup>
  )
}
