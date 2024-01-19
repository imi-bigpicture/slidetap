import { Autocomplete, TextField } from '@mui/material'
import { Action } from 'models/action'
import type { StringAttribute } from 'models/attribute'
import React, { useEffect } from 'react'
import attributeApi from 'services/api/attribute_api'

interface DisplayStringAttributeProps {
  attribute: StringAttribute
  action: Action
  handleAttributeUpdate?: (attribute: StringAttribute) => void
}

export default function DisplayStringAttribute({
  attribute,
  action,
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
          .map((string) => string.value as string)

        setStrings(filteredStrings)
      })
      .catch((x) => {
        console.error('Failed to get strings', x)
      })
  }, [attribute.schema.uid])
  const readOnly = action === Action.VIEW || attribute.schema.readOnly
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
      renderInput={(params) => (
        <TextField
          {...params}
          // label="Code"
          error={attribute.value === undefined && !attribute.schema.optional}
        />
      )}
      onChange={(event, value) => {
        handleStringChange(value)
      }}
    />
  )
}
