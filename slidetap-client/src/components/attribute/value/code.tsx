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

import { MenuItem, Select, Stack, TextField } from '@mui/material'
import React from 'react'
import { Action } from 'src/models/action'
import { Code } from 'src/models/code'
import { CodeAttributeSchema } from 'src/models/schema/attribute_schema'

interface DisplayCodeValueProps {
  value?: Code
  schema: CodeAttributeSchema
  action: Action
  handleValueUpdate: (value: Code) => void
}

export default function DisplayCodeValue({
  value,
  schema,
  action,
  handleValueUpdate,
}: DisplayCodeValueProps): React.ReactElement {
  const readOnly = action === Action.VIEW || schema.readOnly
  const handleCodeChange = (
    attr: 'code' | 'scheme' | 'meaning',
    updatedValue: string | null,
  ): void => {
    // TODO when changing for example code, the scheme and meaning should also be
    // updated if they code is known.
    if (updatedValue === null) {
      updatedValue = ''
    }

    if (value === undefined || value === null) {
      value = {
        code: '',
        scheme: '',
        meaning: '',
      }
    }
    if (attr === 'code') {
      value = {
        code: updatedValue,
        scheme: value !== undefined ? value.scheme : '',
        meaning: value !== undefined ? value.meaning : '',
      }
    } else if (attr === 'scheme') {
      value = {
        code: value !== undefined ? value.code : '',
        scheme: updatedValue,
        meaning: value !== undefined ? value.meaning : '',
      }
    } else if (attr === 'meaning') {
      value = {
        code: value !== undefined ? value.code : '',
        scheme: value !== undefined ? value.scheme : '',
        meaning: updatedValue,
      }
    }
    handleValueUpdate(value)
  }

  return (
    <Stack spacing={1} direction="row">
      <TextField
        label="Code"
        value={value?.code ?? ''}
        error={(value?.code === undefined || value.code === '') && !schema.optional}
        onChange={(event) => {
          handleCodeChange('code', event.target.value)
        }}
        size="small"
        slotProps={{
          input: {
            readOnly: true,
          },
        }}
      />
      {schema.allowedSchemas !== undefined && (
        <Select
          value={value?.scheme ?? ''}
          onChange={(event) => {
            handleCodeChange('scheme', event.target.value)
          }}
          size="small"
          readOnly={readOnly}
        >
          {schema.allowedSchemas.map((allowedSchema) => (
            <MenuItem key={allowedSchema} value={allowedSchema}>
              {allowedSchema}
            </MenuItem>
          ))}
        </Select>
      )}
      {schema.allowedSchemas === undefined && (
        <TextField
          label="Scheme"
          value={value?.scheme ?? ''}
          error={
            (value?.scheme === undefined || value.scheme === '') && !schema.optional
          }
          onChange={(event) => {
            handleCodeChange('scheme', event.target.value)
          }}
          size="small"
          slotProps={{
            input: {
              readOnly: true,
            },
          }}
        />
      )}
      <TextField
        label="Meaning"
        value={value?.meaning ?? ''}
        error={
          (value?.meaning === undefined || value.meaning === '') && !schema.optional
        }
        onChange={(event) => {
          handleCodeChange('meaning', event.target.value)
        }}
        size="small"
        slotProps={{
          input: {
            readOnly: true,
          },
        }}
      />
    </Stack>
  )
}
