import { FormControl, FormLabel } from '@mui/material'
import type { Attribute } from 'models/attribute'
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
import type { Action } from 'models/table_item'
import React from 'react'
import ValueStatusBadge from './mapping_status_badge'
import DisplayBooleanAttribute from './value/boolean'
import DisplayCodeAttribute from './value/code'
import DisplayDatetimeAttribute from './value/datetime'
import DisplayEnumAttribute from './value/enum'
import DisplayListAttribute from './value/list'
import DisplayMeasurementAttribute from './value/measurement'
import DisplayNumericAttribute from './value/numeric'
import DisplayObjectAttribute from './value/object'
import DisplayStringAttribute from './value/string'

interface DisplayAttributeProps {
  attribute: Attribute<any, any>
  action: Action
  hideLabel?: boolean | undefined
  complexAttributeAsButton?: boolean | undefined
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

export default function DisplayAttribute({
  attribute,
  action,
  hideLabel,
  complexAttributeAsButton,
  handleAttributeOpen,
  handleAttributeUpdate,
}: DisplayAttributeProps): React.ReactElement {
  if (isStringAttribute(attribute)) {
    console.log('is string attribute', attribute)
    return (
      <FormControl component="fieldset" variant="standard" fullWidth>
        {hideLabel !== true && (
          <FormLabel component="legend">
            <ValueStatusBadge attribute={attribute} />
          </FormLabel>
        )}
        <DisplayStringAttribute
          attribute={attribute}
          action={action}
          handleAttributeUpdate={handleAttributeUpdate}
        />
      </FormControl>
    )
  }
  if (isDatetimeAttribute(attribute)) {
    return (
      <FormControl component="fieldset" variant="standard" fullWidth>
        {hideLabel !== true && (
          <FormLabel component="legend">
            <ValueStatusBadge attribute={attribute} />
          </FormLabel>
        )}
        <DisplayDatetimeAttribute
          attribute={attribute}
          action={action}
          handleAttributeUpdate={handleAttributeUpdate}
        />
      </FormControl>
    )
  }
  if (isNumericAttribute(attribute)) {
    return (
      <FormControl component="fieldset" variant="standard" fullWidth>
        {hideLabel !== true && (
          <FormLabel component="legend">
            <ValueStatusBadge attribute={attribute} />
          </FormLabel>
        )}
        <DisplayNumericAttribute
          attribute={attribute}
          action={action}
          handleAttributeUpdate={handleAttributeUpdate}
        />
      </FormControl>
    )
  }
  if (isMeasurementAttribute(attribute)) {
    return (
      <FormControl component="fieldset" variant="standard" fullWidth>
        {hideLabel !== true && (
          <FormLabel component="legend">
            <ValueStatusBadge attribute={attribute} />
          </FormLabel>
        )}
        <DisplayMeasurementAttribute
          attribute={attribute}
          action={action}
          handleAttributeUpdate={handleAttributeUpdate}
        />
      </FormControl>
    )
  }
  if (isCodeAttribute(attribute)) {
    return (
      <FormControl component="fieldset" variant="standard" fullWidth>
        {hideLabel !== true && (
          <FormLabel component="legend">
            <ValueStatusBadge attribute={attribute} />
          </FormLabel>
        )}
        <DisplayCodeAttribute
          attribute={attribute}
          action={action}
          handleAttributeUpdate={handleAttributeUpdate}
        />
      </FormControl>
    )
  }
  if (isEnumAttribute(attribute)) {
    return (
      <FormControl component="fieldset" variant="standard" fullWidth>
        {hideLabel !== true && (
          <FormLabel component="legend">
            <ValueStatusBadge attribute={attribute} />
          </FormLabel>
        )}
        <DisplayEnumAttribute
          attribute={attribute}
          action={action}
          handleAttributeUpdate={handleAttributeUpdate}
        />
      </FormControl>
    )
  }
  if (isBooleanAttribute(attribute)) {
    return (
      <FormControl component="fieldset" variant="standard" fullWidth>
        {hideLabel !== true && (
          <FormLabel component="legend">
            <ValueStatusBadge attribute={attribute} />
          </FormLabel>
        )}
        <DisplayBooleanAttribute
          attribute={attribute}
          action={action}
          handleAttributeUpdate={handleAttributeUpdate}
        />
      </FormControl>
    )
  }
  if (isObjectAttribute(attribute)) {
    return (
      <DisplayObjectAttribute
        attribute={attribute}
        action={action}
        complexAttributeAsButton={complexAttributeAsButton ?? false}
        handleAttributeOpen={handleAttributeOpen}
        handleAttributeUpdate={handleAttributeUpdate}
      />
    )
  }
  if (isListAttribute(attribute)) {
    return (
      <FormControl component="fieldset" variant="standard" fullWidth>
        {hideLabel !== true && (
          <FormLabel component="legend">
            <ValueStatusBadge attribute={attribute} />
          </FormLabel>
        )}
        <DisplayListAttribute
          attribute={attribute}
          action={action}
          handleAttributeOpen={handleAttributeOpen}
          handleAttributeUpdate={handleAttributeUpdate}
        />
      </FormControl>
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
        hideLabel={hideLabel}
        handleAttributeOpen={handleAttributeOpen}
        handleAttributeUpdate={handleAttributeUpdate}
      />
    )
  }
  return <></>
  // throw Error('Unhandled attribute' + JSON.stringify(attribute))
}
