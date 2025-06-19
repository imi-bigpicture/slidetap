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

import { FormControl } from '@mui/material'
import Grid from '@mui/material/Grid'

import React from 'react'
import type { ItemDetailAction } from 'src/models/action'
import { AttributeValueTypes, type Attribute } from 'src/models/attribute'
import { Code } from 'src/models/code'
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
  isMeasurementAttributeSchema,
  isNumericAttribute,
  isNumericAttributeSchema,
  isObjectAttribute,
  isObjectAttributeSchema,
  isStringAttribute,
  isStringAttributeSchema,
  isUnionAttribute,
  isUnionAttributeSchema,
} from 'src/models/helpers'
import { Measurement } from 'src/models/measurement'
import { AttributeSchema } from 'src/models/schema/attribute_schema'
import { ValueDisplayType } from 'src/models/value_display_type'
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
  attribute: Attribute<AttributeValueTypes>
  /** The current action performed (viewing, editing, etc.) */
  schema: AttributeSchema
  action: ItemDetailAction
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
    attribute: Attribute<AttributeValueTypes>,
    updateAttribute: (
      tag: string,
      attribute: Attribute<AttributeValueTypes>,
    ) => Attribute<AttributeValueTypes>,
  ) => void
  /** Handle updating the attribute in parent item or attribute. */
  handleAttributeUpdate: (
    tag: string,
    attribute: Attribute<AttributeValueTypes>,
  ) => void
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
          attribute.originalValue === null &&
          attribute.updatedValue === null &&
          attribute.mappedValue === null &&
          schema.optional === false
        }
      >
        <Grid container spacing={1} direction="row">
          <Grid size="grow">
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
          {!schema.readOnly && (
            <Grid size={{ xs: 1 }}>
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
          )}
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
  if (isUnionAttribute(attribute) && isUnionAttributeSchema(schema)) {
    // TODO should display this in an own function
    const value = selectValueToDisplay(attribute, valueToDisplay)
    const valueSchema = schema.attributes.find(
      (childSchema) => childSchema.uid === value?.schemaUid,
    )
    if (value === null || valueSchema === undefined) {
      return <></>
    }

    return (
      <DisplayAttribute
        attribute={value}
        schema={valueSchema}
        action={action}
        handleAttributeOpen={handleAttributeOpen}
        handleAttributeUpdate={handleAttributeUpdate}
        displayAsRoot={displayAsRoot}
      />
    )
  }
  throw Error(
    'Unhandled attribute schema uid ' +
      +attribute.schemaUid +
      ' of type ' +
      attribute.attributeValueType +
      ' and schema ' +
      schema.attributeValueType,
  )
}

interface DisplaySimpleAttributeValueProps {
  /** The attribute to display. */
  attribute: Attribute<AttributeValueTypes>
  schema: AttributeSchema
  /** The current action performed (viewing, editing, etc.) */
  action: ItemDetailAction
  /** The type of value to display. */
  valueToDisplay: ValueDisplayType
  /** Handle updating the attribute in parent item or attribute. */
  handleAttributeUpdate: (
    tag: string,
    attribute: Attribute<AttributeValueTypes>,
  ) => void
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
        handleValueUpdate={(value: string | null) => {
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
        handleValueUpdate={(value: Date | null) => {
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
        handleValueUpdate={(value: number | null) => {
          attribute.updatedValue = value
          handleAttributeUpdate(schema.tag, attribute)
        }}
      />
    )
  }
  if (isMeasurementAttribute(attribute) && isMeasurementAttributeSchema(schema)) {
    return (
      <DisplayMeasurementValue
        value={selectValueToDisplay(attribute, valueToDisplay)}
        schema={schema}
        action={action}
        handleValueUpdate={(value: Measurement | null) => {
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
        handleValueUpdate={(value: Code | null) => {
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
        handleValueUpdate={(value: string | null) => {
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
        handleValueUpdate={(value: boolean | null) => {
          attribute.updatedValue = value
          handleAttributeUpdate(schema.tag, attribute)
        }}
      />
    )
  }
  throw Error(
    'Unhandled attribute schema uid ' +
      attribute.schemaUid +
      ' of type ' +
      attribute.attributeValueType +
      ' and schema ' +
      schema.attributeValueType,
  )
}
