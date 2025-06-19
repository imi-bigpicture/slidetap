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
import { DatetimeAttributeSchema } from 'src/models/schema/attribute_schema'

interface DisplayDatetimeValueProps {
  value: Date | null
  schema: DatetimeAttributeSchema
  action: ItemDetailAction
  handleValueUpdate: (value: Date | null) => void
}

export default function DisplayDatetimeValue({
  value,
  schema,
  action,
  handleValueUpdate,
}: DisplayDatetimeValueProps): React.ReactElement {
  const readOnly = action === ItemDetailAction.VIEW || schema.readOnly
  const handleDatetimeChange = (updatedValue: string): void => {
    handleValueUpdate(new Date(updatedValue))
  }
  return (
    <Stack spacing={1} direction="row" sx={{ margin: 1 }}>
      <TextField
        label={schema.displayName}
        value={value}
        onChange={(event) => {
          handleDatetimeChange(event.target.value)
        }}
        size="small"
        slotProps={{
          input: {
            readOnly: readOnly,
          },
        }}
        error={value === null && !schema.optional}
        fullWidth
      />
    </Stack>
  )
}
