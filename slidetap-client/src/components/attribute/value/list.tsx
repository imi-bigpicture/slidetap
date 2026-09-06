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

import { Add, Delete, ExpandLess, ExpandMore } from '@mui/icons-material'
import {
  Autocomplete,
  Box,
  Button,
  Chip,
  FormHelperText,
  IconButton,
  LinearProgress,
  Stack,
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
import { useTypedText } from './use_typed_text'
import { selectValueToDisplay } from './value_to_display'

/** One value of a list of long text: the box it is written in, and the
 * control that takes it out of the list.
 *
 * A component rather than part of the loop that lays the rows out, so that
 * each row holds what is being typed into it. A list grows and shrinks, and
 * what is held per row has to be held somewhere that comes and goes with it.
 */
function ListChildRow({
  value,
  readOnly,
  atMin,
  removeTitle,
  onCommit,
  onRemove,
}: {
  value: string
  readOnly: boolean
  atMin: boolean
  removeTitle: string
  onCommit: (text: string) => void
  onRemove: () => void
}): React.ReactElement {
  const typed = useTypedText(value, onCommit)
  /** Not while it is being written in: a box is empty until the first letter
   * is typed, and saying so of the one the user has just opened up is telling
   * them off for starting. */
  const [writing, setWriting] = React.useState(false)
  return (
    <Stack direction="row" spacing={0.5} sx={{ alignItems: 'flex-start' }}>
      <TextField
        fullWidth
        multiline
        // Capped rather than growing to the text, so that one long value does
        // not push the rest of the list off the panel.
        maxRows={12}
        size="small"
        value={typed.text}
        error={!writing && typed.text.trim() === ''}
        onChange={(event) => {
          typed.onChange(event.target.value)
        }}
        onFocus={() => {
          setWriting(true)
        }}
        onBlur={() => {
          setWriting(false)
          typed.onBlur()
        }}
        slotProps={{ input: { readOnly } }}
      />
      {!readOnly && (
        <IconButton
          size="small"
          disabled={atMin}
          title={removeTitle}
          onClick={onRemove}
        >
          <Delete fontSize="small" />
        </IconButton>
      )}
    </Stack>
  )
}

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
  /** A child written over several lines. Long text is not something to pick
   * from a list of what has been written before, nor to read back as a word in
   * a single line, so such a list is laid out as the values themselves. */
  const multilineChild =
    isStringAttributeSchema(schema.attribute) && schema.attribute.multiline
  const attributesQuery = useQuery({
    queryKey: queryKeys.attribute.detail(schema.attribute.uid),
    queryFn: async () => {
      return await attributeApi.getAttributesForSchema<Attribute<AttributeValueTypes>>(
        schema.attribute.uid,
      )
    },
    enabled: !multilineChild,
  })
  /** Why the last thing typed was not taken, if it was not. Held so the field
   * can say it: the text itself is cleared as soon as it is read, so a value
   * that is turned away leaves nothing behind to see. */
  const [refused, setRefused] = React.useState<string | null>(null)
  if (!multilineChild && attributesQuery.data === undefined) {
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
  /** What a child says, for the ones whose value is the text itself. */
  const childText = (child: Attribute<AttributeValueTypes>): string => {
    const shown = selectValueToDisplay(child, ValueDisplayType.CURRENT)
    return typeof shown === 'string' ? shown : ''
  }
  const handleChildValueUpdate = (index: number, written: string): void => {
    const children = selectValueToDisplay(attribute, valueToDisplay) ?? []
    handleListChange(
      children.map((item, itemIndex) =>
        itemIndex === index
          ? { ...item, updatedValue: written, displayValue: written }
          : item,
      ),
    )
  }
  const handleChildRemove = (index: number): void => {
    const children = selectValueToDisplay(attribute, valueToDisplay) ?? []
    handleListChange(children.filter((_, itemIndex) => itemIndex !== index))
  }
  /** Add an empty one, which is a box to write in. Nothing is asked of it
   * first: an empty box is what the user is being given, and what is written
   * in it goes straight into the list under it. */
  const handleChildAppend = (): void => {
    const children = selectValueToDisplay(attribute, valueToDisplay) ?? []
    handleListChange([
      ...children,
      newAttribute<AttributeValueTypes>(
        schema.attribute.uid,
        AttributeValueType.STRING,
        '',
        '',
      ),
    ])
  }
  /** Put an edited child back into the list, where it was opened from.
   *
   * Against what the field shows rather than against the edited value, those
   * being the same list only once an edit has been made: an edit to what was
   * imported or mapped starts from what is on screen.
   *
   * Found by its uid where the child carries one, and by where it sits where
   * it does not. A child added elsewhere has no uid until it is written, so
   * several just added all say the nil uid and none is told from the others
   * by it.
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
  const invalid =
    ((value === null || value.length === 0) && !schema.optional) ||
    (schema.minItems !== null && value !== null && value.length < schema.minItems) ||
    (schema.maxItems !== null && value !== null && value.length > schema.maxItems)
  const collapsed = collapse !== undefined && !collapse.open
  /** The name, carrying the chevron that folds the list where it folds. The
   * same label a text field folds itself by, so a folded list and a folded
   * text read alike and neither says its name twice. */
  const fieldLabel =
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
  if (multilineChild) {
    const children = value ?? []
    /** A value nobody has written is not a value. The list holds a place for
     * it either way, so it is the list that is out of order, not just the box
     * it is missing from. */
    const emptyChild = children.some((child) => childText(child).trim() === '')
    const outOfOrder = invalid || emptyChild
    return (
      // A box holding the values, rather than a field standing for them: each
      // is written where it is read, and the rule around them says which list
      // they belong to.
      <Box
        component="fieldset"
        sx={{
          m: 0,
          minWidth: 0,
          px: 1,
          pt: 0,
          pb: 1,
          border: 1,
          borderColor: outOfOrder ? 'error.main' : 'divider',
          borderRadius: 1,
          // Folded, what every other field here leaves behind: the name on a
          // single rule, and nothing below it taking room.
          ...(collapsed && {
            borderWidth: '1px 0 0 0',
            borderRadius: 0,
            px: 0,
            pb: 0,
          }),
        }}
      >
        <Box
          component="legend"
          sx={{
            px: 0.5,
            typography: 'caption',
            color: outOfOrder ? 'error.main' : 'text.secondary',
          }}
        >
          {fieldLabel}
        </Box>
        {!collapsed && (
          <Stack spacing={1}>
            {children.map((child, index) => (
              <ListChildRow
                // By where it sits: a value just added has no uid of its own
                // until it is written, so several of them say the same one.
                key={index}
                value={childText(child)}
                readOnly={readOnly}
                atMin={atMin}
                removeTitle={`Remove ${schema.attribute.displayName}`}
                onCommit={(written) => {
                  handleChildValueUpdate(index, written)
                }}
                onRemove={() => {
                  handleChildRemove(index)
                }}
              />
            ))}
            {!readOnly && (
              <Box>
                <Button
                  size="small"
                  startIcon={<Add />}
                  disabled={atMax}
                  onClick={handleChildAppend}
                  // Lettered like the count below it rather than like a button
                  // that carries the panel: adding one more is a small thing
                  // beside the values themselves.
                  sx={{
                    typography: 'caption',
                    textTransform: 'none',
                    py: 0,
                    px: 0.75,
                    minWidth: 0,
                    '& .MuiButton-startIcon': {
                      mr: 0.5,
                      '& > *:first-of-type': { fontSize: 16 },
                    },
                  }}
                >
                  {`Add ${schema.attribute.displayName}`}
                </Button>
              </Box>
            )}
            {emptyChild ? (
              <FormHelperText error>
                {`Every ${schema.attribute.displayName} needs a value, or take it out of the list.`}
              </FormHelperText>
            ) : (
              helperText !== undefined && (
                <FormHelperText error={invalid}>{helperText}</FormHelperText>
              )
            )}
          </Stack>
        )}
      </Box>
    )
  }
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
      options={atMax ? [] : (attributesQuery.data ?? [])}
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
          label={fieldLabel}
          placeholder={!readOnly ? 'Add ' + schema.attribute.displayName : undefined}
          size="small"
          helperText={refused ?? helperText}
          error={refused !== null || invalid}
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
                // A chip is a line: a value written over several of them, or
                // simply a long one, is cut off at a width the field can hold
                // and read in full by opening it.
                title={labelOf(childAttribute)}
                sx={{ maxWidth: '20em' }}
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
