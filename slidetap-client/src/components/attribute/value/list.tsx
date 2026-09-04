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

import { Add, ExpandLess, ExpandMore } from '@mui/icons-material'
import {
  Autocomplete,
  Box,
  Chip,
  IconButton,
  LinearProgress,
  TextField,
} from '@mui/material'
import { ArrowDropDownIcon } from '@mui/x-date-pickers'
import { useQuery } from '@tanstack/react-query'
import React from 'react'
import { ItemDetailAction } from 'src/models/action'
import type {
  Attribute,
  AttributeValueTypes,
  ListAttribute,
} from 'src/models/attribute'
import { NIL_UID, newAttribute } from 'src/models/attribute'
import { AttributeValueType } from 'src/models/attribute_value_type'
import { isStringAttributeSchema } from 'src/models/helpers'
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
  /** Why the last thing typed was not taken, if it was not. Held so the field
   * can say it: the text itself is cleared as soon as it is read, so a value
   * that is turned away leaves nothing behind to see. */
  const [refused, setRefused] = React.useState<string | null>(null)
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
  const handleListChange = (children: Array<Attribute<AttributeValueTypes>>): void => {
    attribute.updatedValue = children
    handleAttributeUpdate(schema.tag, attribute)
  }
  /** Put an edited child back into the list, where it was opened from.
   *
   * Against what the field shows rather than against the edited value, those
   * being the same list only once an edit has been made: an edit to what was
   * imported or mapped starts from what is on screen.
   *
   * Found by its uid where the child carries one, and by where it sits where
   * it does not. A child added here has no uid until it is written, so several
   * just added all say the nil uid and none is told from the others by it.
   */
  const handleChildUpdate =
    (child: Attribute<AttributeValueTypes>, index: number) =>
    (
      _: string,
      updatedAttribute: Attribute<AttributeValueTypes>,
    ): ListAttribute => {
      const children = selectValueToDisplay(attribute, valueToDisplay) ?? []
      const at =
        child.uid !== NIL_UID
          ? children.findIndex((item) => item.uid === child.uid)
          : index
      if (at < 0 || at >= children.length) {
        return attribute
      }
      attribute.updatedValue = children.map((item, itemIndex) =>
        itemIndex === at ? updatedAttribute : item,
      )
      return attribute
    }
  /** Add a child by opening it, the way the ones too big for the field are
   * written.
   *
   * Put into the list at the first edit rather than when it is opened, so that
   * one opened and then left alone adds nothing. Where it sits is settled at
   * that first edit, the child having no uid to be found by until it is
   * written.
   */
  const handleChildAdd = (): void => {
    let position: number | null = null
    handleAttributeOpen(
      schema.attribute,
      newAttribute<AttributeValueTypes>(
        schema.attribute.uid,
        schema.attribute.attributeValueType,
        null,
        '',
      ),
      (
        _: string,
        updatedAttribute: Attribute<AttributeValueTypes>,
      ): ListAttribute => {
        const children = selectValueToDisplay(attribute, valueToDisplay) ?? []
        if (position === null) {
          position = children.length
          attribute.updatedValue = [...children, updatedAttribute]
        } else {
          attribute.updatedValue = children.map((item, itemIndex) =>
            itemIndex === position ? updatedAttribute : item,
          )
        }
        return attribute
      },
    )
  }
  /** A child the user can say in full by typing it into the field, the text
   * being the whole value and a line of it enough. The others are added by
   * opening one instead: a code or a measurement is more than text, and a
   * string written over several lines wants more room than the field has. */
  const typedChild =
    (isStringAttributeSchema(schema.attribute) && !schema.attribute.multiline) ||
    schema.attribute.attributeValueType === AttributeValueType.NUMERIC
  /** Whether the field reads what is typed into it as a value of its own. */
  const takesTypedText = typedChild && !readOnly
  /** What typed text says: either a child to add, or why it says none.
   * Neither, where nothing but space was typed, there being nothing to add and
   * nothing to tell the user about it. */
  interface TextRead {
    child: Attribute<AttributeValueTypes> | null
    refused: string | null
  }
  const childFromText = (text: string): TextRead => {
    const trimmed = text.trim()
    if (trimmed === '') {
      return { child: null, refused: null }
    }
    if (schema.attribute.attributeValueType === AttributeValueType.STRING) {
      return {
        child: newAttribute(
          schema.attribute.uid,
          AttributeValueType.STRING,
          trimmed,
          trimmed,
        ),
        refused: null,
      }
    }
    const numericSchema = schema.attribute as NumericAttributeSchema
    const number = Number(trimmed)
    if (!Number.isFinite(number)) {
      return { child: null, refused: `"${trimmed}" is not a number.` }
    }
    if (numericSchema.isInteger && !Number.isInteger(number)) {
      return { child: null, refused: 'Only whole numbers can be added.' }
    }
    if (numericSchema.minValue !== null && number < numericSchema.minValue) {
      return {
        child: null,
        refused: `The lowest that can be added is ${numericSchema.minValue}.`,
      }
    }
    if (numericSchema.maxValue !== null && number > numericSchema.maxValue) {
      return {
        child: null,
        refused: `The highest that can be added is ${numericSchema.maxValue}.`,
      }
    }
    return {
      child: newAttribute(
        schema.attribute.uid,
        AttributeValueType.NUMERIC,
        number,
        String(number),
      ),
      refused: null,
    }
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
    let refusal: string | null = null
    for (const item of value) {
      if (typeof item !== 'string') {
        children.push(item)
        continue
      }
      const read = childFromText(item)
      if (read.child !== null) {
        children.push(read.child)
      } else if (read.refused !== null) {
        refusal = read.refused
      }
    }
    if (
      refusal === null &&
      schema.maxItems !== null &&
      children.length > schema.maxItems
    ) {
      refusal = `At most ${schema.maxItems} can be added.`
    }
    if (
      refusal === null &&
      schema.minItems !== null &&
      children.length < schema.minItems
    ) {
      refusal = `At least ${schema.minItems} must be kept.`
    }
    setRefused(refusal)
    // Nothing of a refused change is kept, so that an attribute nobody has
    // edited is not recorded as edited by a change that was turned away.
    if (refusal !== null) {
      return
    }
    handleListChange(children)
  }
  const value = selectValueToDisplay(attribute, valueToDisplay)
  /** Shown where the field does not take what is typed into it, that being the
   * only other way of adding a child. Its own click, kept from the field
   * underneath, which would read it as asking for the options. */
  const addChild =
    readOnly || takesTypedText ? null : (
      <IconButton
        className="list-add-child"
        size="small"
        disabled={atMax}
        title={`Add ${schema.attribute.displayName}`}
        onMouseDown={(event) => {
          event.stopPropagation()
        }}
        onClick={(event) => {
          event.stopPropagation()
          handleChildAdd()
        }}
      >
        <Add fontSize="small" />
      </IconButton>
    )
  return (
    <Autocomplete
      multiple
      freeSolo={takesTypedText}
      // Text still in the field when it loses focus is read as though it had
      // been entered, so that typing a value and then saving does not lose it.
      autoSelect={takesTypedText}
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
      // Only where nothing is typed: losing focus reads a highlighted option
      // ahead of the text itself, and the first option is highlighted before
      // the user has so much as looked at it.
      autoHighlight={!takesTypedText}
      fullWidth={true}
      limitTags={3}
      size="small"
      getOptionLabel={labelOf}
      filterSelectedOptions
      popupIcon={!readOnly ? <ArrowDropDownIcon /> : null}
      renderInput={(params) => (
        <TextField
          {...params}
          slotProps={{
            ...params.slotProps,
            input: {
              ...params.slotProps.input,
              endAdornment: (
                <React.Fragment>
                  {addChild}
                  {params.slotProps.input.endAdornment}
                </React.Fragment>
              ),
            },
          }}
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
          // Only where typing into the field is what adds one. Elsewhere it is
          // the button that adds, and an empty box asking to be typed in is an
          // invitation to nothing.
          placeholder={
            takesTypedText ? 'Add ' + schema.attribute.displayName : undefined
          }
          size="small"
          helperText={refused ?? helperText}
          error={
            refused !== null ||
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
                          handleChildUpdate(childAttribute, index),
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
      onInputChange={(_, __, reason) => {
        // What the user types, and nothing else: the field empties itself just
        // after a value is read, which is when a refusal was set.
        if (reason === 'input' && refused !== null) {
          setRefused(null)
        }
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
            '& .MuiChip-root, & .MuiInputBase-input, & .MuiAutocomplete-endAdornment, & .list-add-child':
              {
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
