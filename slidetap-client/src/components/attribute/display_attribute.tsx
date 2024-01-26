import { FormControl, FormLabel, Grid } from '@mui/material'
import type { Action } from 'models/action'
import {
  ValueDisplayType,
  type Attribute,
  type Code,
  type Measurement,
} from 'models/attribute'
import {
  isBooleanAttribute,
  isCodeAttribute,
  isDatetimeAttribute,
  isEnumAttribute,
  isListAttribute,
  isMeasurementAttribute,
  isNumericAttribute,
  isObjectAttribute,
  isStringAttribute,
  isUnionAttribute,
} from 'models/helpers'
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
import ValueMenu from './value_menu'

interface DisplayAttributeProps {
  /** The attribute to display. */
  attribute: Attribute<any, any>
  /** The current action performed (viewing, editing, etc.) */
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
    attribute: Attribute<any, any>,
    updateAttribute: (attribute: Attribute<any, any>) => Attribute<any, any>,
  ) => void
  /** Handle updating the attribute in parent item or attribute. */
  handleAttributeUpdate: (attribute: Attribute<any, any>) => void
}

export default function DisplayAttribute({
  attribute,
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
      <FormControl component="fieldset" variant="standard" fullWidth>
        <FormLabel component="legend">{attribute.schema.displayName}</FormLabel>
        <Grid container spacing={1} direction="row" sx={{ margin: 1 }}>
          <Grid item xs>
            {valueToDisplay !== ValueDisplayType.MAPPED && (
              <DisplaySimpleAttributeValue
                attribute={attribute}
                action={action}
                displayOriginalValue={valueToDisplay === ValueDisplayType.ORIGINAL}
                handleAttributeUpdate={handleAttributeUpdate}
              />
            )}
            {valueToDisplay === ValueDisplayType.MAPPED && (
              <DisplayAttributeMapping attribute={attribute} />
            )}
          </Grid>
          <Grid item xs={2}>
            <ValueMenu
              attribute={attribute}
              action={action}
              valueToDisplay={valueToDisplay}
              setValueToDisplay={setValueToDisplay}
              handleAttributeUpdate={handleAttributeUpdate}
            />
          </Grid>
        </Grid>
      </FormControl>
    )
  }
  if (isObjectAttribute(attribute)) {
    return (
      <DisplayObjectAttribute
        attribute={attribute}
        action={action}
        handleAttributeOpen={handleAttributeOpen}
        handleAttributeUpdate={handleAttributeUpdate}
        displayAsRoot={displayAsRoot}
      />
    )
  }
  if (isListAttribute(attribute)) {
    return (
      <DisplayListAttribute
        attribute={attribute}
        action={action}
        handleAttributeOpen={handleAttributeOpen}
        handleAttributeUpdate={handleAttributeUpdate}
      />
    )
  }
  if (
    isUnionAttribute(attribute) &&
    attribute.value !== null &&
    attribute.value !== undefined
  ) {
    // TODO should display this in an own function
    return (
      <DisplayAttribute
        attribute={attribute.value}
        action={action}
        handleAttributeOpen={handleAttributeOpen}
        handleAttributeUpdate={handleAttributeUpdate}
        displayAsRoot={displayAsRoot}
      />
    )
  }
  throw Error('Unhandled attribute' + JSON.stringify(attribute))
}

interface DisplaySimpleAttributeValueProps {
  /** The attribute to display. */
  attribute: Attribute<any, any>
  /** The current action performed (viewing, editing, etc.) */
  action: Action
  /** The type of value to display. */
  displayOriginalValue: boolean
  /** Handle updating the attribute in parent item or attribute. */
  handleAttributeUpdate: (attribute: Attribute<any, any>) => void
}

function DisplaySimpleAttributeValue({
  attribute,
  action,
  displayOriginalValue,
  handleAttributeUpdate,
}: DisplaySimpleAttributeValueProps): React.ReactElement {
  if (isStringAttribute(attribute)) {
    return (
      <DisplayStringValue
        value={displayOriginalValue ? attribute.originalValue : attribute.value}
        schema={attribute.schema}
        action={action}
        handleValueUpdate={(value: string) => {
          attribute.value = value
          handleAttributeUpdate(attribute)
        }}
      />
    )
  }
  if (isDatetimeAttribute(attribute)) {
    return (
      <DisplayDatetimeValue
        value={displayOriginalValue ? attribute.originalValue : attribute.value}
        schema={attribute.schema}
        action={action}
        handleValueUpdate={(value: Date) => {
          attribute.value = value
          handleAttributeUpdate(attribute)
        }}
      />
    )
  }
  if (isNumericAttribute(attribute)) {
    return (
      <DisplayNumericValue
        value={displayOriginalValue ? attribute.originalValue : attribute.value}
        schema={attribute.schema}
        action={action}
        handleValueUpdate={(value: number) => {
          attribute.value = value
          handleAttributeUpdate(attribute)
        }}
      />
    )
  }
  if (isMeasurementAttribute(attribute)) {
    return (
      <DisplayMeasurementValue
        value={displayOriginalValue ? attribute.originalValue : attribute.value}
        schema={attribute.schema}
        action={action}
        handleValueUpdate={(value: Measurement) => {
          attribute.value = value
          handleAttributeUpdate(attribute)
        }}
      />
    )
  }
  if (isCodeAttribute(attribute)) {
    return (
      <DisplayCodeValue
        value={displayOriginalValue ? attribute.originalValue : attribute.value}
        schema={attribute.schema}
        action={action}
        handleValueUpdate={(value: Code) => {
          attribute.value = value
          handleAttributeUpdate(attribute)
        }}
      />
    )
  }
  if (isEnumAttribute(attribute)) {
    return (
      <DisplayEnumValue
        value={attribute.value}
        schema={attribute.schema}
        action={action}
        handleValueUpdate={(value: string) => {
          attribute.value = value
          handleAttributeUpdate(attribute)
        }}
      />
    )
  }
  if (isBooleanAttribute(attribute)) {
    return (
      <DisplayBooleanValue
        value={displayOriginalValue ? attribute.originalValue : attribute.value}
        schema={attribute.schema}
        action={action}
        handleValueUpdate={(value: boolean) => {
          attribute.value = value
          handleAttributeUpdate(attribute)
        }}
      />
    )
  }
  throw Error('Unhandled attribute' + JSON.stringify(attribute))
}
