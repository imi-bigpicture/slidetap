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

import { ExpandLess, ExpandMore } from '@mui/icons-material'
import { Autocomplete, Box, Chip, LinearProgress, TextField } from '@mui/material'
import { ArrowDropDownIcon } from '@mui/x-date-pickers'
import { useQuery } from '@tanstack/react-query'
import React from 'react'
import { ItemDetailAction } from 'src/models/action'
import type {
  Attribute,
  AttributeValueTypes,
  ListAttribute,
} from 'src/models/attribute'
import {
  AttributeSchema,
  ListAttributeSchema,
} from 'src/models/schema/attribute_schema'
import { ValueDisplayType } from 'src/models/value_display_type'
import attributeApi from 'src/services/api/attribute_api'
import { queryKeys } from 'src/services/query_keys'
import { selectValueToDisplay } from './value_to_display'

interface DisplayListAttributeProps {
  attribute: ListAttribute
  schema: ListAttributeSchema
  action: ItemDetailAction
  /** Handle adding new attribute to display open and display as nested attributes.
   * When an attribute should be opened, the attribute and a function for updating
   * the attribute in the parent attribute should be added.
   * @param attribute - Attribute to open
   * @param updateAttribute - Function to update the attribute in the parent attribute
   */
  valueToDisplay: ValueDisplayType
  handleAttributeOpen: (
    schema: AttributeSchema,
    attribute: Attribute<AttributeValueTypes>,
    updateAttribute: (
      tag: string,
      attribute: Attribute<AttributeValueTypes>,
    ) => Attribute<AttributeValueTypes>,
  ) => void
  handleAttributeUpdate: (
    tag: string,
    attribute: Attribute<AttributeValueTypes>,
  ) => void
  /** Folds the list away behind its own label, the way a text field does. */
  collapse?: { open: boolean; onToggle: () => void }
}

export default function DisplayListAttribute({
  attribute,
  schema,
  action,
  valueToDisplay,
  handleAttributeOpen,
  handleAttributeUpdate,
  collapse,
}: DisplayListAttributeProps): React.ReactElement {
  const attributesQuery = useQuery({
    queryKey: queryKeys.attribute.detail(schema.attribute.uid),
    queryFn: async () => {
      return await attributeApi.getAttributesForSchema<Attribute<AttributeValueTypes>>(
        schema.attribute.uid,
      )
    },
  })
  if (attributesQuery.data === undefined) {
    return <LinearProgress />
  }
  const readOnly = action === ItemDetailAction.VIEW || schema.readOnly
  const currentCount = (selectValueToDisplay(attribute, ValueDisplayType.CURRENT) ?? []).length
  const atMax = schema.maxItems !== null && currentCount >= schema.maxItems
  const atMin = schema.minItems !== null && currentCount <= schema.minItems
  const helperText =
    schema.minItems !== null && schema.maxItems !== null
      ? `${currentCount} / ${schema.minItems}–${schema.maxItems}`
      : schema.maxItems !== null
        ? `${currentCount} / ${schema.maxItems}`
        : schema.minItems !== null
          ? `${currentCount} (min ${schema.minItems})`
          : undefined
  const handleListChange = (value: Array<Attribute<AttributeValueTypes>>): void => {
    if (schema.maxItems !== null && value.length > schema.maxItems) {
      return
    }
    if (schema.minItems !== null && value.length < schema.minItems) {
      return
    }
    attribute.updatedValue = value
    handleAttributeUpdate(schema.tag, attribute)
  }
  const handleOwnAttributeUpdate = (
    _: string,
    updatedAttribute: Attribute<AttributeValueTypes>,
  ): ListAttribute => {
    // Should attribute.updatedValue be used?
    attribute.updatedValue =
      attribute.updatedValue !== null
        ? attribute.updatedValue.map((item) =>
            item.uid === updatedAttribute.uid ? updatedAttribute : item,
          )
        : null
    return attribute
  }
  const value = selectValueToDisplay(attribute, valueToDisplay)
  return (
    <Autocomplete
      multiple
      title={schema.displayName}
      value={value ?? []}
      // options={[
      //   ...new Map(
      //     attributesQuery.data.map((attribute) => [attribute.displayValue, attribute]),
      //   ).values(),
      // ]}
      options={atMax ? [] : attributesQuery.data}
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
          // The same label a text field folds itself by, so a folded list and
          // a folded text read alike and neither says its name twice.
          label={
            collapse === undefined ? (
              schema.displayName
            ) : (
              <Box
                component="span"
                onClick={collapse.onToggle}
                sx={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 0.25,
                  cursor: 'pointer',
                }}
              >
                {collapse.open ? (
                  <ExpandLess fontSize="inherit" />
                ) : (
                  <ExpandMore fontSize="inherit" />
                )}
                {schema.displayName}
              </Box>
            )
          }
          placeholder={!readOnly ? 'Add ' + schema.attribute.displayName : undefined}
          size="small"
          helperText={helperText}
          error={
            ((value === null || value.length === 0) && !schema.optional) ||
            (schema.minItems !== null && value !== null && value.length < schema.minItems) ||
            (schema.maxItems !== null && value !== null && value.length > schema.maxItems)
          }
        />
      )}
      renderValue={(value, getTagProps) => (
        <React.Fragment>
          {value.map((childAttribute, index) => {
            const { key, onDelete, ...other } = getTagProps({ index })
            return (
              <Chip
                key={key}
                {...other}
                onDelete={atMin ? undefined : onDelete}
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
      onChange={(_, value) => {
        handleListChange(value)
      }}
      sx={{
        // Closed, only the top edge and its label are left — the same rule a
        // closed text field keeps, broken around the name.
        ...(collapse !== undefined &&
          !collapse.open && {
            '&:hover .MuiOutlinedInput-notchedOutline': {
              borderColor: 'text.primary',
            },
            // The field inside is inline, which in a block would leave a line
            // box behind — a closed field would still take a line of height.
            display: 'flex',
            // Doubled to outweigh the padding the autocomplete gives its own
            // input, which is written more specifically than a plain override.
            // Not hidden overflow: the rule is drawn by a fieldset sitting just
            // outside the closed-up box, and clipping the box clips the rule.
            '&& .MuiInputBase-root': {
              minHeight: 0,
              height: 0,
              p: 0,
            },
            // The values themselves, the input and the arrow: everything the
            // field holds goes with it, leaving the rule and the name.
            '& .MuiChip-root, & .MuiInputBase-input, & .MuiAutocomplete-endAdornment': {
              display: 'none',
            },
            '& .MuiOutlinedInput-notchedOutline': {
              borderBottom: 0,
              borderLeft: 0,
              borderRight: 0,
              borderRadius: 0,
            },
            '& .MuiFormHelperText-root': { display: 'none' },
          }),
      }}
    />
  )
}
