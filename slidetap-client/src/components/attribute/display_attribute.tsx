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
  IsListAttribute,
  isMeasurementAttribute,
  isNumericAttribute,
  IsObjectAttribute,
  isStringAttribute,
  IsUnionAttribute,
} from 'models/helpers'


interface DisplayAttributeProps {
  attribute: Attribute<any, any>
  hideLabel?: boolean | undefined
  handleChangeAttribute?: (attributeUid: string) => void
}

export default function DisplayAttribute({
  attribute,
  hideLabel,
  handleChangeAttribute
}: DisplayAttributeProps): React.ReactElement {
  if (isStringAttribute(attribute)) {
    return <DisplayStringAttribute attribute={attribute} hideLabel={hideLabel} />
  }
  if (isDatetimeAttribute(attribute)) {
    return <DisplayDatetimeAttribute attribute={attribute} hideLabel={hideLabel} />
  }
  if (isNumericAttribute(attribute)) {
    return <DisplayNumericAttribute attribute={attribute} hideLabel={hideLabel} />
  }
  if (isMeasurementAttribute(attribute)) {
    return <DisplayMeasurementAttribute attribute={attribute} hideLabel={hideLabel} />
  }
  if (isCodeAttribute(attribute)) {
    return <DisplayCodeAttribute attribute={attribute} hideLabel={hideLabel} />
  }
  if (isEnumAttribute(attribute)) {
    return <DisplayEnumAttribute attribute={attribute} hideLabel={hideLabel} />
  }
  if (isBooleanAttribute(attribute)) {
    return <DisplayBooleanAttribute attribute={attribute} hideLabel={hideLabel} />
  }
  if (IsObjectAttribute(attribute)) {
    return <DisplayObjectAttribute
      attribute={attribute}
      hideLabel={hideLabel}
      handleChangeAttribute={handleChangeAttribute}
    />
  }
  if (IsListAttribute(attribute)) {
    return <DisplayListAttribute attribute={attribute} hideLabel={hideLabel} />
  }
  if (IsUnionAttribute(attribute) && attribute.value !== undefined) {
    // TODO should display this in an own function
    return <DisplayAttribute attribute={attribute.value} hideLabel={hideLabel} />
  }
  throw Error('Unhandled attribute' + JSON.stringify(attribute))
}
