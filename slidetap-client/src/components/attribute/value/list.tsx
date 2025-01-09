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
import { AttributeSchema, ListAttributeSchema } from 'models/schema/attribute_schema'
import { ValueDisplayType } from 'models/value_display_type'
import React from 'react'
import attributeApi from 'services/api/attribute_api'
import { selectValueToDisplay } from './value_to_display'

interface DisplayListAttributeProps {
  attribute: ListAttribute
  schema: ListAttributeSchema
  action: Action
  /** Handle adding new attribute to display open and display as nested attributes.
   * When an attribute should be opened, the attribute and a function for updating
   * the attribute in the parent attribute should be added.
   * @param attribute - Attribute to open
   * @param updateAttribute - Function to update the attribute in the parent attribute
   */
  valueToDisplay: ValueDisplayType
  handleAttributeOpen: (
    schema: AttributeSchema,
    attribute: Attribute<any>,
    updateAttribute: (tag: string, attribute: Attribute<any>) => Attribute<any>,
  ) => void
  handleAttributeUpdate: (tag: string, attribute: Attribute<any>) => void
}

export default function DisplayListAttribute({
  attribute,
  schema,
  action,
  valueToDisplay,
  handleAttributeOpen,
  handleAttributeUpdate,
}: DisplayListAttributeProps): React.ReactElement {
  const attributesQuery = useQuery({
    queryKey: ['attributes', schema.attribute.uid],
    queryFn: async () => {
      return await attributeApi.getAttributesForSchema<Attribute<any>>(
        schema.attribute.uid,
      )
    },
  })
  if (attributesQuery.data === undefined) {
    return <LinearProgress />
  }
  const readOnly = action === Action.VIEW || schema.readOnly
  const handleListChange = (value: Array<Attribute<any>>): void => {
    attribute.updatedValue = value
    handleAttributeUpdate(schema.tag, attribute)
  }
  const handleOwnAttributeUpdate = (
    tag: string,
    updatedAttribute: Attribute<any>,
  ): ListAttribute => {
    // Should attribute.updatedValue be used?
    attribute.updatedValue = attribute.updatedValue?.map((item) =>
      item.uid === updatedAttribute.uid ? updatedAttribute : item,
    )
    return attribute
  }
  const value = selectValueToDisplay(attribute, valueToDisplay)
  return (
    <Autocomplete
      multiple
      value={value ?? []}
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
          label={schema.attribute.displayName}
          placeholder={!readOnly ? 'Add ' + schema.attribute.displayName : undefined}
          size="small"
          error={(value === undefined || value.length === 0) && !schema.optional}
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
                  handleAttributeOpen(
                    schema.attribute,
                    childAttribute,
                    handleOwnAttributeUpdate,
                  )
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
