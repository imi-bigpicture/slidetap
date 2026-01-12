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

import { Grid, MenuItem, TextField } from '@mui/material'
import React from 'react'
import { ItemDetailAction } from 'src/models/action'
import { Code } from 'src/models/code'
import { CodeAttributeSchema } from 'src/models/schema/attribute_schema'

interface DisplayCodeValueProps {
  value: Code | null
  schema: CodeAttributeSchema
  action: ItemDetailAction
  handleValueUpdate: (value: Code | null) => void
}

export default function DisplayCodeValue({
  value,
  schema,
  action,
  handleValueUpdate,
}: DisplayCodeValueProps): React.ReactElement {
  const readOnly = action === ItemDetailAction.VIEW || schema.readOnly
  const handleCodeChange = (
    attr: 'code' | 'scheme' | 'meaning',
    updatedValue: string | null,
  ): void => {
    if (updatedValue === null) {
      updatedValue = ''
    }

    if (value === undefined || value === null) {
      value = {
        code: '',
        scheme: '',
        meaning: '',
        schemeVersion: null,
      }
    }
    if (attr === 'code') {
      value = {
        code: updatedValue,
        scheme: value !== undefined ? value.scheme : '',
        meaning: value !== undefined ? value.meaning : '',
        schemeVersion: null,
      }
    } else if (attr === 'scheme') {
      value = {
        code: value !== undefined ? value.code : '',
        scheme: updatedValue,
        meaning: value !== undefined ? value.meaning : '',
        schemeVersion: null,
      }
    } else if (attr === 'meaning') {
      value = {
        code: value !== undefined ? value.code : '',
        scheme: value !== undefined ? value.scheme : '',
        meaning: updatedValue,
        schemeVersion: null,
      }
    }
    handleValueUpdate(value)
  }
  const validCode = value !== null && value.code !== ''
  const validScheme =
    value !== null &&
    value.scheme !== '' &&
    (schema.allowedSchemas === null || schema.allowedSchemas.includes(value.scheme))
  const validMeaning = value !== null && value.meaning !== ''
  const nullIsOk = schema.optional && value === null
  return (
    <Grid container spacing={1}>
      <Grid size={4}>
        <TextField
          label={schema.displayName + ' code'}
          required={!schema.optional}
          value={value?.code ?? ''}
          error={!validCode && !nullIsOk}
          onChange={(event) => {
            handleCodeChange('code', event.target.value)
          }}
          size="small"
          slotProps={{
            input: {
              readOnly: readOnly,
            },
            inputLabel: {
              shrink: true,
            },
          }}
          fullWidth={true}
        />
      </Grid>
      <Grid size={3}>
        {schema.allowedSchemas ? (
          <TextField
            label="Scheme"
            required={!schema.optional}
            value={value?.scheme ?? ''}
            error={!validScheme && !nullIsOk}
            onChange={(event) => {
              handleCodeChange('scheme', event.target.value)
            }}
            size="small"
            slotProps={{
              input: {
                readOnly: readOnly,
              },
              inputLabel: {
                shrink: true,
              },
            }}
            fullWidth={true}
          >
            {schema.allowedSchemas.map((allowedSchema) => (
              <MenuItem key={allowedSchema} value={allowedSchema}>
                {allowedSchema}
              </MenuItem>
            ))}
          </TextField>
        ) : (
          <TextField
            label="Scheme"
            required={!schema.optional}
            value={value?.scheme ?? ''}
            error={!validScheme && !nullIsOk}
            onChange={(event) => {
              handleCodeChange('scheme', event.target.value)
            }}
            size="small"
            slotProps={{
              input: {
                readOnly: readOnly,
              },
              inputLabel: {
                shrink: true,
              },
            }}
            fullWidth={true}
          />
        )}
      </Grid>
      <Grid size={5}>
        <TextField
          label="Meaning"
          required={!schema.optional}
          value={value?.meaning ?? ''}
          error={!validMeaning && !nullIsOk}
          onChange={(event) => {
            handleCodeChange('meaning', event.target.value)
          }}
          size="small"
          slotProps={{
            input: {
              readOnly: true,
            },
            inputLabel: {
              shrink: true,
            },
          }}
          fullWidth={true}
        />
      </Grid>
    </Grid>
  )
}
