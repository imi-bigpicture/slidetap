import React from 'react'
import type { Attribute } from 'models/attribute'
import DisplayStringAttribute from './value/string'
import DisplayDatetimeAttribute from './value/datetime'
import DisplayNumericAttribute from './value/numeric'
import DisplayMeasurementAttribute from './value/measurement'
import DisplayCodeAttribute from './value/code'
import DisplayObjectAttribute from './value/object'
import DisplayListAttribute from './value/list'
import DisplayEnumAttribute from './value/enum'
import DisplayBooleanAttribute from './value/boolean'
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
import { Button, FormControl, FormLabel } from '@mui/material'
import ValueStatusBadge from './mapping_status_badge'
import type { Action } from 'models/table_item'

interface DisplayAttributeProps {
  attribute: Attribute<any, any>
  action: Action
  hideLabel?: boolean | undefined
  complexAttributeAsButton?: boolean | undefined
  handleAttributeOpen?: (attribute: Attribute<any, any>) => void
  handleAttributeUpdate?: (attribute: Attribute<any, any>) => void
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
    if (complexAttributeAsButton === true) {
      return (
        <Button
          id={attribute.uid}
          onClick={() => {
            if (handleAttributeOpen === undefined) {
              return
            }
            handleAttributeOpen(attribute)
          }}
        >
          {attribute.schema.displayName}
        </Button>
      )
    }
    return (
      <DisplayObjectAttribute
        attribute={attribute}
        action={action}
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
      />
    )
  }
  return <></>
  // throw Error('Unhandled attribute' + JSON.stringify(attribute))
}
