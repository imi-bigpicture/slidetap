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

import { Autocomplete, Chip, Stack, TextField } from '@mui/material'
import React from 'react'
import { ItemDetailAction } from 'src/models/action'
import type { CodeAttribute } from 'src/models/attribute'
import type { Code, CodeSuggestion } from 'src/models/code'
import { CodeAttributeSchema } from 'src/models/schema/attribute_schema'
import { ValueDisplayType } from 'src/models/value_display_type'
import attributeApi from 'src/services/api/attribute_api'
import { selectValueToDisplay } from './value_to_display'

interface DisplayCodeValueProps {
  attribute: CodeAttribute
  schema: CodeAttributeSchema
  action: ItemDetailAction
  valueToDisplay: ValueDisplayType
  handleAttributeUpdate: (attribute: CodeAttribute) => void
}

function formatCode(code: Code): string {
  return `${code.code} · ${code.scheme} · ${code.meaning}`
}

function optionLabel(option: CodeSuggestion | string): string {
  if (typeof option === 'string') return option
  return formatCode(option.code)
}

export default function DisplayCodeValue({
  attribute,
  schema,
  action,
  valueToDisplay,
  handleAttributeUpdate,
}: DisplayCodeValueProps): React.ReactElement {
  const readOnly = action === ItemDetailAction.VIEW || schema.readOnly
  const displayedCode = selectValueToDisplay<Code>(attribute, valueToDisplay)
  const mappableValue = attribute.mappableValue ?? ''

  const currentValue: CodeSuggestion | string | null = displayedCode
    ? { code: displayedCode, match: 'code' }
    : mappableValue !== ''
      ? mappableValue
      : null

  const committedText = displayedCode
    ? formatCode(displayedCode)
    : mappableValue

  const [inputValue, setInputValue] = React.useState<string>(committedText)
  const [options, setOptions] = React.useState<CodeSuggestion[]>([])
  const [loading, setLoading] = React.useState(false)

  // Re-sync the input when the parent commits a new value to the attribute.
  React.useEffect(() => {
    setInputValue(committedText)
    // Intentionally depend only on committedText: it captures every relevant
    // attribute field that affects the display.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [committedText])

  React.useEffect(() => {
    if (readOnly) return
    let cancelled = false
    setLoading(true)
    const handle = window.setTimeout(() => {
      attributeApi
        .searchCodes(schema.uid, inputValue, 20)
        .then((results) => {
          if (!cancelled) setOptions(results)
        })
        .catch(() => {
          if (!cancelled) setOptions([])
        })
        .finally(() => {
          if (!cancelled) setLoading(false)
        })
    }, 250)
    return () => {
      cancelled = true
      window.clearTimeout(handle)
    }
  }, [inputValue, schema.uid, readOnly])

  const validValue =
    displayedCode !== null &&
    displayedCode.code !== '' &&
    (schema.allowedSchemas === null ||
      schema.allowedSchemas.includes(displayedCode.scheme))
  const validMappable = mappableValue !== ''
  const nullIsOk = schema.optional && !validValue && !validMappable
  const error = !validValue && !validMappable && !nullIsOk

  const helperText = (() => {
    if (validValue) return undefined
    if (validMappable) return 'Unmapped — will be resolved on save'
    return undefined
  })()

  const handleChange = (
    _: React.SyntheticEvent,
    newValue: CodeSuggestion | string | null,
  ): void => {
    if (newValue === null) {
      handleAttributeUpdate({
        ...attribute,
        updatedValue: null,
        mappableValue: null,
        mappingItemUid: null,
      })
      return
    }
    if (typeof newValue === 'string') {
      const trimmed = newValue.trim()
      if (trimmed === '') {
        handleAttributeUpdate({
          ...attribute,
          updatedValue: null,
          mappableValue: null,
          mappingItemUid: null,
        })
        return
      }
      // No-op when the input still matches the committed value (autoSelect
      // can fire a string event when the user just blurs without editing).
      if (trimmed === committedText) return
      handleAttributeUpdate({
        ...attribute,
        updatedValue: null,
        mappableValue: trimmed,
        mappingItemUid: null,
      })
      return
    }
    handleAttributeUpdate({
      ...attribute,
      updatedValue: newValue.code,
      mappableValue: null,
      mappingItemUid: null,
    })
  }

  return (
    <Autocomplete<CodeSuggestion, false, false, true>
      freeSolo
      autoSelect
      fullWidth
      size="small"
      readOnly={readOnly}
      loading={loading}
      options={options}
      value={currentValue}
      inputValue={inputValue}
      onInputChange={(_, value) => setInputValue(value)}
      onChange={handleChange}
      filterOptions={(x) => x}
      getOptionLabel={optionLabel}
      isOptionEqualToValue={(option, value) => {
        if (typeof value === 'string' || typeof option === 'string') return false
        return (
          option.code.code === value.code.code &&
          option.code.scheme === value.code.scheme
        )
      }}
      renderOption={(props, option) => (
        <li
          {...props}
          key={`${option.code.code}-${option.code.scheme}-${option.mappableValue ?? ''}`}
        >
          <Stack
            direction="row"
            spacing={1}
            sx={{ width: '100%', alignItems: 'center' }}
          >
            {option.match === 'mappable' && option.mappableValue && (
              <Chip
                size="small"
                label={option.mappableValue}
                variant="outlined"
              />
            )}
            <span style={{ flexGrow: 1 }}>
              <strong>{option.code.code}</strong>
              {' · '}
              <em>{option.code.scheme}</em>
              {' · '}
              {option.code.meaning}
            </span>
          </Stack>
        </li>
      )}
      renderInput={(params) => (
        <TextField
          {...params}
          label={schema.displayName}
          required={!schema.optional}
          error={error}
          helperText={helperText}
          slotProps={{
            ...params.slotProps,
            inputLabel: { ...params.slotProps.inputLabel, shrink: true },
          }}
        />
      )}
    />
  )
}
