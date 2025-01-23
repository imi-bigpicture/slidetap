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

import { MenuItem, Select, Stack } from '@mui/material'
import React from 'react'
import { Action } from 'src/models/action'
import { EnumAttributeSchema } from 'src/models/schema/attribute_schema'

interface DisplayEnumValueProps {
  value?: string
  schema: EnumAttributeSchema
  action: Action
  handleValueUpdate: (value: string) => void
}

export default function DisplayEnumValue({
  value,
  schema,
  action,
  handleValueUpdate,
}: DisplayEnumValueProps): React.ReactElement {
  const readOnly = action === Action.VIEW || schema.readOnly
  return (
    <Stack spacing={1} direction="row" sx={{ margin: 1 }}>
      <Select
        value={value}
        onChange={(event) => {
          handleValueUpdate(event.target.value)
        }}
        size="small"
        readOnly={readOnly}
      >
        {schema.allowedValues.map((allowedValue) => (
          <MenuItem key={allowedValue} value={allowedValue}>
            {allowedValue}
          </MenuItem>
        ))}
      </Select>
    </Stack>
  )
}
