import React, { useEffect } from 'react'
import { Autocomplete, Chip, TextField } from '@mui/material'
import type { Attribute, ListAttribute } from 'models/attribute'
import attributeApi from 'services/api/attribute_api'
import { ArrowDropDownIcon } from '@mui/x-date-pickers'
import { Action } from 'models/table_item'

interface DisplayListAttributeProps {
  attribute: ListAttribute
  action: Action
  handleAttributeOpen?: (
    attribute: Attribute<any, any>,
    parentAttribute?: Attribute<any, any>,
  ) => void
  handleAttributeUpdate?: (attribute: Attribute<any, any>) => void
}

export default function DisplayListAttribute({
  attribute,
  action,
  handleAttributeOpen,
  handleAttributeUpdate,
}: DisplayListAttributeProps): React.ReactElement {
  const [attributes, setAttributes] = React.useState<Array<Attribute<any, any>>>([])

  useEffect(() => {
    attributeApi
      .getAttributesForSchema<Attribute<any, any>>(attribute.schema.attribute.uid)
      .then((attributes) => {
        console.log(attributes)
        setAttributes(attributes)
      })
      .catch((x) => {
        console.error('Failed to get attributes', x)
      })
  }, [attribute.schema.attribute.uid])
  const readOnly = action === Action.VIEW
  const handleListChange = (value: Array<Attribute<any, any>>): void => {
    attribute.value = value
    handleAttributeUpdate?.(attribute)
  }
  return (
    <Autocomplete
      multiple
      value={attribute.value ?? []}
      options={[
        ...new Map(
          attributes.map((attribute) => [attribute.displayValue, attribute]),
        ).values(),
      ]}
      readOnly={readOnly}
      autoComplete={true}
      autoHighlight={true}
      fullWidth={true}
      limitTags={3}
      size="small"
      getOptionLabel={(option) => option.displayValue}
      filterSelectedOptions
      popupIcon={!readOnly ? <ArrowDropDownIcon /> : null}
      renderInput={(params) => (
        <TextField
          {...params}
          label={attribute.schema.attribute.displayName}
          placeholder={
            !readOnly ? 'Add ' + attribute.schema.attribute.displayName : undefined
          }
          size="small"
        />
      )}
      renderTags={
        handleAttributeOpen !== undefined
          ? (value, getTagProps) => (
              <React.Fragment>
                {value.map((option, index) => {
                  const { key, ...other } = getTagProps({ index })
                  return (
                    <Chip
                      key={key}
                      {...other}
                      label={option.displayValue}
                      onClick={() => {
                        handleAttributeOpen(option)
                      }}
                    />
                  )
                })}
              </React.Fragment>
            )
          : undefined
      }
      isOptionEqualToValue={(option, value) => option.uid === value.uid}
      onChange={(event, value) => {
        handleListChange(value)
      }}
    />
  )
}
