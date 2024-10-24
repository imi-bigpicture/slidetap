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

import { Autocomplete, Chip, LinearProgress, TextField } from '@mui/material'
import { ArrowDropDownIcon } from '@mui/x-date-pickers'
import { useQuery } from '@tanstack/react-query'
import { Action } from 'models/action'
import type { Attribute, ListAttribute } from 'models/attribute'
import React from 'react'
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
  const attributesQuery = useQuery({
    queryKey: ['attributes', attribute.schema.attribute.uid],
    queryFn: async () => {
      return await attributeApi.getAttributesForSchema<Attribute<any, any>>(
        attribute.schema.attribute.uid,
      )
    },
  })
  if (attributesQuery.data === undefined) {
    return <LinearProgress />
  }
  const readOnly = action === Action.VIEW || attribute.schema.readOnly
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
          attributesQuery.data.map((attribute) => [attribute.displayValue, attribute]),
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
          error={
            (attribute.value === undefined || attribute.value.length === 0) &&
            !attribute.schema.optional
          }
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
