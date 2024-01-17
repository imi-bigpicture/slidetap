import { Autocomplete, Chip, TextField } from '@mui/material'
import { ArrowDropDownIcon } from '@mui/x-date-pickers'
import type { Attribute, ListAttribute } from 'models/attribute'
import { Action } from 'models/table_item'
import React, { useEffect } from 'react'
import attributeApi from 'services/api/attribute_api'

interface DisplayListAttributeProps {
  attribute: ListAttribute
  action: Action
  /** Handle adding new attribute to display open and display as nested attributes.
   * When an attribute should be opened, the attribute and a function for updating
   * the attribute in the parent attribute should be added.
   * @param attribute - Attribute to open
   * @param updateAttribute - Function to update the attribute in the parent attribute
   */
  handleAttributeOpen: (
    attribute: Attribute<any, any>,
    updateAttribute: (attribute: Attribute<any, any>) => Attribute<any, any>,
  ) => void
  handleAttributeUpdate: (attribute: Attribute<any, any>) => void
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
        setAttributes(attributes)
      })
      .catch((x) => {
        console.error('Failed to get attributes', x)
      })
  }, [attribute.schema.attribute.uid])
  const readOnly = action === Action.VIEW
  const handleListChange = (value: Array<Attribute<any, any>>): void => {
    attribute.value = value
    handleAttributeUpdate(attribute)
  }
  const handleOwnAttributeUpdate = (
    updatedAttribute: Attribute<any, any>,
  ): Attribute<any, any> => {
    attribute.value = attribute.value?.map((item) =>
      item.uid === updatedAttribute.uid ? updatedAttribute : item,
    )
    return attribute
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
      renderTags={(value, getTagProps) => (
        <React.Fragment>
          {value.map((childAttribute, index) => {
            const { key, ...other } = getTagProps({ index })
            return (
              <Chip
                key={key}
                {...other}
                label={childAttribute.displayValue}
                onClick={() => {
                  handleAttributeOpen(childAttribute, handleOwnAttributeUpdate)
                }}
              />
            )
          })}
        </React.Fragment>
      )}
      isOptionEqualToValue={(option, value) =>
        option.displayValue === value.displayValue
      }
      onChange={(event, value) => {
        handleListChange(value)
      }}
    />
  )
}
