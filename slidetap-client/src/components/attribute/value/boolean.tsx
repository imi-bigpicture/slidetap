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
import { Action } from 'src/models/action'
import { BooleanAttributeSchema } from 'src/models/schema/attribute_schema'

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
          readOnly ? <Radio size="small" readOnly={true} /> : <Radio size="small" />
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
