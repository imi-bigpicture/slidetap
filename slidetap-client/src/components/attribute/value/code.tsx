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

import { Autocomplete, LinearProgress, Stack, TextField } from '@mui/material'
import { Action } from 'models/action'
import { type Code, type CodeAttribute } from 'models/attribute'
import type { CodeAttributeSchema } from 'models/schema'
import React from 'react'
import { useQuery } from 'react-query'
import attributeApi from 'services/api/attribute_api'

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
  const codesQuery = useQuery({
    queryKey: ['codes', schema.uid],
    queryFn: async () => {
      return await attributeApi.getAttributesForSchema<CodeAttribute>(schema.uid)
    },
    select: (data) => {
      return data
        .filter((code) => code !== null)
        .filter((code) => code !== undefined)
        .filter((code) => code.value !== undefined)
        .filter((code) => code.value !== null)
        .map((code) => code.value as Code)
    },
  })
  if (codesQuery.data === undefined) {
    return <LinearProgress />
  }

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
      const matchingCodes = codesQuery.data.find(
        (code) => code.code === updatedValue && value?.scheme === code.scheme,
      )
      if (matchingCodes !== undefined) {
        value = matchingCodes
      } else {
        value = {
          code: updatedValue,
          scheme: value !== undefined ? value.scheme : '',
          meaning: value !== undefined ? value.meaning : '',
        }
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
      <Autocomplete
        value={value?.code ?? ''}
        options={[...new Set(codesQuery.data.map((code) => code.code))]}
        freeSolo={true}
        autoComplete={true}
        autoHighlight={true}
        autoSelect={true}
        fullWidth={true}
        readOnly={readOnly}
        size="small"
        renderInput={(params) => (
          <TextField
            {...params}
            label="Code"
            error={(value?.code === undefined || value.code === '') && !schema.optional}
          />
        )}
        onChange={(event, value) => {
          handleCodeChange('code', value)
        }}
      />
      <Autocomplete
        value={value?.scheme ?? ''}
        options={[...new Set(codesQuery.data.map((code) => code.scheme))]}
        freeSolo={true}
        autoComplete={true}
        autoHighlight={true}
        autoSelect={true}
        fullWidth={true}
        readOnly={readOnly}
        size="small"
        renderInput={(params) => (
          <TextField
            {...params}
            label="Scheme"
            error={
              (value?.scheme === undefined || value.scheme === '') && !schema.optional
            }
          />
        )}
        onChange={(event, value) => {
          handleCodeChange('scheme', value)
        }}
      />
      <Autocomplete
        value={value?.meaning ?? ''}
        options={[...new Set(codesQuery.data.map((code) => code.meaning))]}
        freeSolo={true}
        autoComplete={true}
        autoHighlight={true}
        autoSelect={true}
        fullWidth={true}
        readOnly={readOnly}
        size="small"
        renderInput={(params) => (
          <TextField
            {...params}
            label="Meaning"
            error={
              (value?.meaning === undefined || value.meaning === '') && !schema.optional
            }
          />
        )}
        onChange={(event, value) => {
          handleCodeChange('meaning', value)
        }}
      />
    </Stack>
  )
}
