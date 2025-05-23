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
import { Action } from 'src/models/action'
import { NumericAttributeSchema } from 'src/models/schema/attribute_schema'

interface DisplayNumericValueProps {
  value?: number
  schema: NumericAttributeSchema
  action: Action
  handleValueUpdate: (value: number) => void
}

export default function DisplayNumericValue({
  value,
  schema,
  action,
  handleValueUpdate,
}: DisplayNumericValueProps): React.ReactElement {
  const readOnly = action === Action.VIEW || schema.readOnly

  const handleNumericChange = (updatedValue: string): void => {
    handleValueUpdate(parseFloat(updatedValue))
  }
  return (
    <Stack spacing={1} direction="row" sx={{ margin: 1 }}>
      <TextField
        label="Value"
        value={value}
        onChange={(event) => {
          handleNumericChange(event.target.value)
        }}
        type="number"
        size="small"
        InputProps={{ readOnly, inputMode: 'numeric' }}
        error={value === undefined && !schema.optional}
      />
    </Stack>
  )
}
