import { Checkbox, FormControlLabel, Radio, RadioGroup, Stack } from '@mui/material'
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
    <Stack spacing={1} direction="row">
      <RadioGroup
        value={value}
        onChange={(event) => {
          handleBooleanChange(event.target.value)
        }}
      >
        <Stack direction="row" spacing={2}>
          <FormControlLabel
            value="true"
            control={
              readOnly ? (
                <Radio size="small" readOnly={true} />
              ) : (
                <Checkbox size="small" />
              )
            }
            checked={value}
            label={schema.trueDisplayValue}
          />
          <FormControlLabel
            value="false"
            control={
              readOnly ? (
                <Radio size="small" readOnly={true} />
              ) : (
                <Checkbox size="small" />
              )
            }
            label={schema.falseDisplayValue}
            checked={value === false}
          />
        </Stack>
      </RadioGroup>
    </Stack>
  )
}
