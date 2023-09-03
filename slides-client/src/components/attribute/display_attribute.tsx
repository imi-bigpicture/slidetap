import React from 'react'
import { Attribute } from 'models/attribute'
import DisplayStringAttribute from './value/string'
import DisplayDatetimeAttribute from './value/datetime'
import DisplayNumericAttribute from './value/numeric'
import DisplayMeasurementAttribute from './value/measurement'
import DisplayCodeAttribute from './value/code'
import {
    isCodeAttribute, isDatetimeAttribute,
    IsListAttribute,
    isMeasurementAttribute, isNumericAttribute, IsObjectAttribute,
    isStringAttribute
} from 'models/helpers'
import DisplayObjectAttribute from './value/object'
import DisplayListAttribute from './value/list'

interface DisplayAttributeProps {
    attribute: Attribute<any, any>
    hideLabel?: boolean | undefined
}

export default function DisplayAttribute (
    { attribute, hideLabel }: DisplayAttributeProps
): React.ReactElement {
    if (isStringAttribute(attribute)) {
        return (
            <DisplayStringAttribute
                attribute={attribute}
                hideLabel={hideLabel}
            />
        )
    }
    if (isDatetimeAttribute(attribute)) {
        return (
            <DisplayDatetimeAttribute
                attribute={attribute}
                hideLabel={hideLabel}
            />
        )
    }
    if (isNumericAttribute(attribute)) {
        return (
            <DisplayNumericAttribute
                attribute={attribute}
                hideLabel={hideLabel}
            />
        )
    }
    if (isMeasurementAttribute(attribute)) {
        return (
            <DisplayMeasurementAttribute
                attribute={attribute}
                hideLabel={hideLabel}
            />
        )
    }
    if (isCodeAttribute(attribute)) {
        return (
            <DisplayCodeAttribute
                attribute={attribute}
                hideLabel={hideLabel}
            />
        )
    }
    if (IsObjectAttribute(attribute)) {
        return (
            <DisplayObjectAttribute
                attribute={attribute}
                hideLabel={hideLabel}
            />
        )
    }
    if (IsListAttribute(attribute)) {
        return (
            <DisplayListAttribute
                attribute={attribute}
                hideLabel={hideLabel}
            />
        )
    }
    throw Error('Unhandled attribute' + JSON.stringify(attribute))
}
