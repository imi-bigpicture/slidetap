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

import { FormControl, FormLabel } from '@mui/material'
import Grid from '@mui/material/Grid2'

import type { Action } from 'models/action'
import { type Attribute } from 'models/attribute'
import { Code } from 'models/code'
import {
  isBooleanAttribute,
  isBooleanAttributeSchema,
  isCodeAttribute,
  isCodeAttributeSchema,
  isDatetimeAttribute,
  isDatetimeAttributeSchema,
  isEnumAttribute,
  isEnumAttributeSchema,
  isListAttribute,
  isListAttributeSchema,
  isMeasurementAttribute,
  isNumericAttribute,
  isNumericAttributeSchema,
  isObjectAttribute,
  isObjectAttributeSchema,
  isStringAttribute,
  isStringAttributeSchema,
  isUnionAttribute,
} from 'models/helpers'
import { Measurement } from 'models/measurement'
import { AttributeSchema } from 'models/schema/attribute_schema'
import { ValueDisplayType } from 'models/value_display_type'
import React from 'react'
import DisplayAttributeMapping from './display_attribute_mapping'
import DisplayBooleanValue from './value/boolean'
import DisplayCodeValue from './value/code'
import DisplayDatetimeValue from './value/datetime'
import DisplayEnumValue from './value/enum'
import DisplayListAttribute from './value/list'
import DisplayMeasurementValue from './value/measurement'
import DisplayNumericValue from './value/numeric'
import DisplayObjectAttribute from './value/object'
import DisplayStringValue from './value/string'
import { selectValueToDisplay } from './value/value_to_display'
import ValueMenu from './value_menu'

interface DisplayAttributeProps {
  /** The attribute to display. */
  attribute: Attribute<any>
  /** The current action performed (viewing, editing, etc.) */
  schema: AttributeSchema
  action: Action
  /** If the attribute should be displayed as root without a label. */
  displayAsRoot?: boolean
  /** Handle adding new attribute to display open and display as nested attributes.
   * When an attribute should be opened, the attribute and a function for updating
   * the attribute in the parent attribute should be added.
   * @param attribute - Attribute to open
   * @param updateAttribute - Function to update the attribute in the parent attribute
   */
  handleAttributeOpen: (
    schema: AttributeSchema,
    attribute: Attribute<any>,
    updateAttribute: (tag: string, attribute: Attribute<any>) => Attribute<any>,
  ) => void
  /** Handle updating the attribute in parent item or attribute. */
  handleAttributeUpdate: (tag: string, attribute: Attribute<any>) => void
}

export default function DisplayAttribute({
  attribute,
  schema,
  action,
  displayAsRoot,
  handleAttributeOpen,
  handleAttributeUpdate,
}: DisplayAttributeProps): React.ReactElement {
  const [valueToDisplay, setValueToDisplay] = React.useState<ValueDisplayType>(
    ValueDisplayType.CURRENT,
  )
  if (
    !isObjectAttribute(attribute) &&
    !isListAttribute(attribute) &&
    !isUnionAttribute(attribute)
  ) {
    return (
      <FormControl
        size="small"
        component="fieldset"
        variant="standard"
        fullWidth
        error={
          attribute.originalValue === undefined &&
          attribute.updatedValue === undefined &&
          attribute.mappedValue === undefined &&
          schema.optional === false
        }
      >
        <FormLabel component="legend">{schema.displayName}</FormLabel>
        <Grid container spacing={1} direction="row" sx={{ margin: 1 }}>
          <Grid size={{ xs: 10 }}>
            {valueToDisplay !== ValueDisplayType.MAPPED && (
              <DisplaySimpleAttributeValue
                attribute={attribute}
                schema={schema}
                action={action}
                valueToDisplay={valueToDisplay}
                handleAttributeUpdate={handleAttributeUpdate}
              />
            )}
            {valueToDisplay === ValueDisplayType.MAPPED && (
              <DisplayAttributeMapping attribute={attribute} />
            )}
          </Grid>
          <Grid size={{ xs: 2 }}>
            <ValueMenu
              attribute={attribute}
              action={action}
              valueToDisplay={valueToDisplay}
              setValueToDisplay={setValueToDisplay}
              handleAttributeUpdate={(attribute) =>
                handleAttributeUpdate(schema.tag, attribute)
              }
            />
          </Grid>
        </Grid>
      </FormControl>
    )
  }
  if (isObjectAttribute(attribute) && isObjectAttributeSchema(schema)) {
    return (
      <DisplayObjectAttribute
        attribute={attribute}
        schema={schema}
        action={action}
        handleAttributeOpen={handleAttributeOpen}
        handleAttributeUpdate={handleAttributeUpdate}
        displayAsRoot={displayAsRoot}
        valueToDisplay={valueToDisplay}
      />
    )
  }
  if (isListAttribute(attribute) && isListAttributeSchema(schema)) {
    return (
      <DisplayListAttribute
        attribute={attribute}
        schema={schema}
        action={action}
        handleAttributeOpen={handleAttributeOpen}
        handleAttributeUpdate={handleAttributeUpdate}
        valueToDisplay={valueToDisplay}
      />
    )
  }
  if (
    isUnionAttribute(attribute) &&
    attribute.value !== null &&
    attribute.value !== undefined
  ) {
    // TODO should display this in an own function
    const value = selectValueToDisplay(attribute, valueToDisplay)
    return (
      <DisplayAttribute
        attribute={value}
        action={action}
        handleAttributeOpen={handleAttributeOpen}
        handleAttributeUpdate={handleAttributeUpdate}
        displayAsRoot={displayAsRoot}
      />
    )
  }
  throw Error(
    'Unhandled attribute' +
      JSON.stringify(attribute) +
      'Schema' +
      JSON.stringify(schema),
  )
}

interface DisplaySimpleAttributeValueProps {
  /** The attribute to display. */
  attribute: Attribute<any>
  schema: AttributeSchema
  /** The current action performed (viewing, editing, etc.) */
  action: Action
  /** The type of value to display. */
  valueToDisplay: ValueDisplayType
  /** Handle updating the attribute in parent item or attribute. */
  handleAttributeUpdate: (tag: string, attribute: Attribute<any>) => void
}

function DisplaySimpleAttributeValue({
  attribute,
  schema,
  action,
  valueToDisplay,
  handleAttributeUpdate,
}: DisplaySimpleAttributeValueProps): React.ReactElement {
  if (isStringAttribute(attribute) && isStringAttributeSchema(schema)) {
    return (
      <DisplayStringValue
        value={selectValueToDisplay(attribute, valueToDisplay)}
        schema={schema}
        action={action}
        handleValueUpdate={(value: string) => {
          attribute.updatedValue = value
          handleAttributeUpdate(schema.tag, attribute)
        }}
      />
    )
  }
  if (isDatetimeAttribute(attribute) && isDatetimeAttributeSchema(schema)) {
    return (
      <DisplayDatetimeValue
        value={selectValueToDisplay(attribute, valueToDisplay)}
        schema={schema}
        action={action}
        handleValueUpdate={(value: Date) => {
          attribute.updatedValue = value
          handleAttributeUpdate(schema.tag, attribute)
        }}
      />
    )
  }
  if (isNumericAttribute(attribute) && isNumericAttributeSchema(schema)) {
    return (
      <DisplayNumericValue
        value={selectValueToDisplay(attribute, valueToDisplay)}
        schema={schema}
        action={action}
        handleValueUpdate={(value: number) => {
          attribute.updatedValue = value
          handleAttributeUpdate(schema.tag, attribute)
        }}
      />
    )
  }
  if (isMeasurementAttribute(attribute) && isMeasurementAttribute(schema)) {
    return (
      <DisplayMeasurementValue
        value={selectValueToDisplay(attribute, valueToDisplay)}
        schema={schema}
        action={action}
        handleValueUpdate={(value: Measurement) => {
          attribute.updatedValue = value
          handleAttributeUpdate(schema.tag, attribute)
        }}
      />
    )
  }
  if (isCodeAttribute(attribute) && isCodeAttributeSchema(schema)) {
    return (
      <DisplayCodeValue
        value={selectValueToDisplay(attribute, valueToDisplay)}
        schema={schema}
        action={action}
        handleValueUpdate={(value: Code) => {
          attribute.updatedValue = value
          handleAttributeUpdate(schema.tag, attribute)
        }}
      />
    )
  }
  if (isEnumAttribute(attribute) && isEnumAttributeSchema(schema)) {
    return (
      <DisplayEnumValue
        value={selectValueToDisplay(attribute, valueToDisplay)}
        schema={schema}
        action={action}
        handleValueUpdate={(value: string) => {
          attribute.updatedValue = value
          handleAttributeUpdate(schema.tag, attribute)
        }}
      />
    )
  }
  if (isBooleanAttribute(attribute) && isBooleanAttributeSchema(schema)) {
    return (
      <DisplayBooleanValue
        value={selectValueToDisplay(attribute, valueToDisplay)}
        schema={schema}
        action={action}
        handleValueUpdate={(value: boolean) => {
          attribute.updatedValue = value
          handleAttributeUpdate(schema.tag, attribute)
        }}
      />
    )
  }
  throw Error(
    'Unhandled attribute' +
      JSON.stringify(attribute) +
      'Schema' +
      JSON.stringify(schema),
  )
}
