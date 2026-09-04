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
import { newAttribute } from 'src/models/attribute'
import { AttributeValueType } from 'src/models/attribute_value_type'
import {
  AttributeSchema,
  ListAttributeSchema,
  NumericAttributeSchema,
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
  /** Put an edited child back where it was taken from.
   *
   * By where it sits rather than by its uid: a child added here has none of
   * its own until it is written --- the server mints one --- so two just added
   * are the same uid, and a uid is not what the list opened one of them by.
   */
  const handleChildUpdate =
    (index: number) =>
    (
      _: string,
      updatedAttribute: Attribute<AttributeValueTypes>,
    ): ListAttribute => {
      // Should attribute.updatedValue be used?
      attribute.updatedValue =
        attribute.updatedValue !== null
          ? attribute.updatedValue.map((item, itemIndex) =>
              itemIndex === index ? updatedAttribute : item,
            )
          : null
      return attribute
    }
  /** A child the user can say in full by typing it, the text being the whole
   * value. The others — a code, a measurement, anything holding attributes of
   * its own — are more than a line of text, and are added by editing one
   * rather than by typing into the field. */
  const typedChild =
    schema.attribute.attributeValueType === AttributeValueType.STRING ||
    schema.attribute.attributeValueType === AttributeValueType.NUMERIC
  /** The typed text as a child attribute, or null where it does not say one.
   * Refusing here rather than adding a chip that holds nothing leaves the text
   * in the field, where the user can see what was not taken and correct it. */
  const childFromText = (
    text: string,
  ): Attribute<AttributeValueTypes> | null => {
    const trimmed = text.trim()
    if (trimmed === '') {
      return null
    }
    if (schema.attribute.attributeValueType === AttributeValueType.STRING) {
      return newAttribute(
        schema.attribute.uid,
        AttributeValueType.STRING,
        trimmed,
        trimmed,
      )
    }
    const numericSchema = schema.attribute as NumericAttributeSchema
    const number = Number(trimmed)
    if (!Number.isFinite(number)) {
      return null
    }
    if (numericSchema.isInteger && !Number.isInteger(number)) {
      return null
    }
    if (numericSchema.minValue !== null && number < numericSchema.minValue) {
      return null
    }
    if (numericSchema.maxValue !== null && number > numericSchema.maxValue) {
      return null
    }
    return newAttribute(
      schema.attribute.uid,
      AttributeValueType.NUMERIC,
      number,
      String(number),
    )
  }
  /** What a chip and an option are labelled by. Under `freeSolo` the field
   * types its own contents as text as well, which the value never is here: it
   * is read back as a child attribute before it is put in. */
  const labelOf = (item: Attribute<AttributeValueTypes> | string): string =>
    typeof item === 'string' ? item : item.displayValue
  /** What the field gives back, which under `freeSolo` holds the typed text
   * itself where the user did not pick one of the options. */
  const handleFieldChange = (
    value: ReadonlyArray<Attribute<AttributeValueTypes> | string>,
  ): void => {
    const children: Array<Attribute<AttributeValueTypes>> = []
    for (const item of value) {
      if (typeof item !== 'string') {
        children.push(item)
        continue
      }
      const child = childFromText(item)
      if (child !== null) {
        children.push(child)
      }
    }
    handleListChange(children)
  }
  const value = selectValueToDisplay(attribute, valueToDisplay)
  return (
    <Autocomplete
      multiple
      freeSolo={typedChild && !readOnly}
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
      getOptionLabel={labelOf}
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
                label={labelOf(childAttribute)}
                onClick={
                  typeof childAttribute === 'string'
                    ? undefined
                    : () => {
                        handleAttributeOpen(
                          schema.attribute,
                          childAttribute,
                          handleChildUpdate(index),
                        )
                      }
                }
              />
            )
          })}
        </React.Fragment>
      )}
      isOptionEqualToValue={(option, value) => labelOf(option) === labelOf(value)}
      onChange={(_, value) => {
        handleFieldChange(value)
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
