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

import { Autocomplete, TextField } from '@mui/material'
import { Action } from 'models/action'
import { type StringAttribute } from 'models/attribute'
import type { StringAttributeSchema } from 'models/schema'
import React, { useEffect } from 'react'
import attributeApi from 'services/api/attribute_api'

interface DisplayStringValueProps {
  value?: string
  schema: StringAttributeSchema
  action: Action
  handleValueUpdate: (value: string) => void
}

export default function DisplayStringValue({
  value,
  schema,
  action,
  handleValueUpdate,
}: DisplayStringValueProps): React.ReactElement {
  const [strings, setStrings] = React.useState<string[]>([])

  useEffect(() => {
    attributeApi
      .getAttributesForSchema<StringAttribute>(schema.uid)
      .then((strings) => {
        const filteredStrings = strings
          .filter((string) => string !== null)
          .filter((string) => string !== undefined)
          .filter((string) => string.value !== undefined)
          .filter((string) => string.value !== null)
          .map((string) => string.value as string)

        setStrings(filteredStrings)
      })
      .catch((x) => {
        console.error('Failed to get strings', x)
      })
  }, [schema.uid])
  const readOnly = action === Action.VIEW || schema.readOnly

  return (
    <Autocomplete
      value={value ?? ''}
      options={[...new Set(strings)]}
      freeSolo={true}
      autoSelect={true}
      readOnly={readOnly}
      size="small"
      renderInput={(params) => (
        <TextField
          {...params}
          error={(value === undefined || value === '') && !schema.optional}
        />
      )}
      onChange={(event, value) => {
        handleValueUpdate(value ?? '')
      }}
    />
  )
}
