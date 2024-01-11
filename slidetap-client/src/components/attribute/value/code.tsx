import React from 'react'
import { Stack, TextField } from '@mui/material'
import type { CodeAttribute } from 'models/attribute'

interface DisplayCodeAttributeProps {
  attribute: CodeAttribute
  handleAttributeUpdate?: (attribute: CodeAttribute) => void
}

export default function DisplayCodeAttribute({
  attribute,
  handleAttributeUpdate,
}: DisplayCodeAttributeProps): React.ReactElement {
  const readOnly = handleAttributeUpdate === undefined
  const handleCodeChange = (
    attr: 'code' | 'scheme' | 'meaning',
    value: string,
  ): void => {
    if (attribute.value === undefined || attribute.value === null) {
      attribute.value = {
        code: '',
        scheme: '',
        meaning: '',
      }
    }
    if (attr === 'code') {
      attribute.value = {
        code: value,
        scheme: attribute.value !== undefined ? attribute.value.scheme : '',
        meaning: attribute.value !== undefined ? attribute.value.meaning : '',
      }
    } else if (attr === 'scheme') {
      attribute.value = {
        code: attribute.value !== undefined ? attribute.value.code : '',
        scheme: value,
        meaning: attribute.value !== undefined ? attribute.value.meaning : '',
      }
    } else if (attr === 'meaning') {
      attribute.value = {
        code: attribute.value !== undefined ? attribute.value.code : '',
        scheme: attribute.value !== undefined ? attribute.value.scheme : '',
        meaning: value,
      }
    }
    handleAttributeUpdate?.(attribute)
  }
  return (
    <Stack spacing={1} direction="row" sx={{ margin: 2 }}>
      <TextField
        label="Code"
        value={attribute.value?.code}
        onChange={(event) => {
          handleCodeChange('code', event.target.value)
        }}
        InputProps={{ readOnly }}
      />
      <TextField
        label="Scheme"
        value={attribute.value?.scheme}
        onChange={(event) => {
          handleCodeChange('scheme', event.target.value)
        }}
        InputProps={{ readOnly }}
      />
      <TextField
        label="Meaning"
        value={attribute.value?.meaning}
        onChange={(event) => {
          handleCodeChange('meaning', event.target.value)
        }}
        InputProps={{ readOnly }}
      />
    </Stack>
  )
}
