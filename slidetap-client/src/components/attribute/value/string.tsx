import React, { useEffect } from 'react'
import { Autocomplete, Stack, TextField } from '@mui/material'
import type { StringAttribute } from 'models/attribute'
import attributeApi from 'services/api/attribute_api'

interface DisplayStringAttributeProps {
  attribute: StringAttribute
  handleAttributeUpdate?: (attribute: StringAttribute) => void
}

export default function DisplayStringAttribute({
  attribute,
  handleAttributeUpdate,
}: DisplayStringAttributeProps): React.ReactElement {
  const [strings, setStrings] = React.useState<string[]>([])

  useEffect(() => {
    attributeApi
      .getAttributesForSchema<StringAttribute>(attribute.schema.uid)
      .then((strings) => {
        const filteredStrings = strings
          .filter((string) => string !== null)
          .filter((string) => string !== undefined)
          .filter((string) => string.value !== undefined)
          .filter((string) => string.value !== null)

        setStrings(filteredStrings)
      })
      .catch((x) => {
        console.error('Failed to get strings', x)
      })
  }, [attribute.schema.uid])
  const readOnly = handleAttributeUpdate === undefined
  const handleStringChange = (value: string | null): void => {
    if (value === null) {
      value = ''
    }
    attribute.value = value
    handleAttributeUpdate?.(attribute)
  }
  return (
    <Autocomplete
      value={attribute.value ?? ''}
      options={[...new Set(strings)]}
      freeSolo={true}
      readOnly={readOnly}
      renderInput={(params) => <TextField {...params} label="Code" />}
      onChange={(event, value) => {
        handleStringChange(value)
      }}
    />
  )
}
