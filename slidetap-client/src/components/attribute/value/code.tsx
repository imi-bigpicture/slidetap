import React, { useEffect } from 'react'
import { Autocomplete, Stack, TextField } from '@mui/material'
import type { Code, CodeAttribute } from 'models/attribute'
import attributeApi from 'services/api/attribute_api'
import { Action } from 'models/table_item'
interface DisplayCodeAttributeProps {
  attribute: CodeAttribute
  action: Action
  handleAttributeUpdate?: (attribute: CodeAttribute) => void
}

export default function DisplayCodeAttribute({
  attribute,
  action,
  handleAttributeUpdate,
}: DisplayCodeAttributeProps): React.ReactElement {
  const [codes, setCodes] = React.useState<Code[]>([])

  useEffect(() => {
    attributeApi
      .getAttributesForSchema<CodeAttribute>(attribute.schema.uid)
      .then((codes) => {
        const filteredCodes = codes
          .filter((code) => code !== null)
          .filter((code) => code !== undefined)
          .filter((code) => code.value !== undefined)
          .filter((code) => code.value !== null)
          .map((code) => code.value)

        setCodes(filteredCodes)
      })
      .catch((x) => {
        console.error('Failed to get codes', x)
      })
  }, [attribute.schema.uid])
  const readOnly = action === Action.VIEW
  const handleCodeChange = (
    attr: 'code' | 'scheme' | 'meaning',
    value: string | null,
  ): void => {
    // TODO when changing for example code, the scheme and meaning should also be
    // updated if they code is known.
    if (value === null) {
      value = ''
    }
    if (attribute.value === undefined || attribute.value === null) {
      attribute.value = {
        code: '',
        scheme: '',
        meaning: '',
      }
    }
    if (attr === 'code') {
      const matchingCodes = codes.find(
        (code) => code.code === value && attribute.value?.scheme === code.scheme,
      )
      if (matchingCodes !== undefined) {
        attribute.value = matchingCodes
      } else {
        attribute.value = {
          code: value,
          scheme: attribute.value !== undefined ? attribute.value.scheme : '',
          meaning: attribute.value !== undefined ? attribute.value.meaning : '',
        }
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
    <Stack spacing={1} direction="row" sx={{ margin: 1 }}>
      <Autocomplete
        value={attribute.value?.code ?? ''}
        options={[...new Set(codes.map((code) => code.code))]}
        freeSolo={true}
        autoComplete={true}
        autoHighlight={true}
        autoSelect={true}
        fullWidth={true}
        readOnly={readOnly}
        size="small"
        renderInput={(params) => <TextField {...params} label="Code" />}
        onChange={(event, value) => {
          handleCodeChange('code', value)
        }}
      />
      <Autocomplete
        value={attribute.value?.scheme ?? ''}
        options={[...new Set(codes.map((code) => code.scheme))]}
        freeSolo={true}
        autoComplete={true}
        autoHighlight={true}
        autoSelect={true}
        fullWidth={true}
        readOnly={readOnly}
        size="small"
        renderInput={(params) => <TextField {...params} label="Scheme" />}
        onChange={(event, value) => {
          handleCodeChange('scheme', value)
        }}
      />
      <Autocomplete
        value={attribute.value?.meaning ?? ''}
        options={[...new Set(codes.map((code) => code.meaning))]}
        freeSolo={true}
        autoComplete={true}
        autoHighlight={true}
        autoSelect={true}
        fullWidth={true}
        readOnly={readOnly}
        size="small"
        renderInput={(params) => <TextField {...params} label="Meaning" />}
        onChange={(event, value) => {
          handleCodeChange('meaning', value)
        }}
      />
    </Stack>
  )
}
