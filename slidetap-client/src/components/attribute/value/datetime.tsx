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
import { Action } from 'models/action'
import type { DatetimeAttributeSchema } from 'models/schema'
import React from 'react'

interface DisplayDatetimeValueProps {
  value?: Date
  schema: DatetimeAttributeSchema
  action: Action
  handleValueUpdate: (value: Date) => void
}

export default function DisplayDatetimeValue({
  value,
  schema,
  action,
  handleValueUpdate,
}: DisplayDatetimeValueProps): React.ReactElement {
  const readOnly = action === Action.VIEW || schema.readOnly
  const handleDatetimeChange = (updatedValue: string): void => {
    handleValueUpdate(new Date(updatedValue))
  }
  return (
    <Stack spacing={2} direction="row" sx={{ margin: 2 }}>
      <TextField
        value={value}
        onChange={(event) => {
          handleDatetimeChange(event.target.value)
        }}
        size="small"
        InputProps={{ readOnly }}
        error={value === undefined && !schema.optional}
      />
    </Stack>
  )
}
