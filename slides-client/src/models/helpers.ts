import { Attribute, AttributeValueType, CodeAttribute, DatetimeAttribute, MeasurementAttribute, NumericAttribute, StringAttribute, ObjectAttribute, ListAttribute } from './attribute'

export function isAttribute (object: any): object is Attribute<any, any> {
    return (
        object != null &&
        'attributeValueType' in object
    )
}

export function isStringAttribute (object: any): object is StringAttribute {
    return (
        isAttribute(object) && object.attributeValueType === AttributeValueType.STRING
    )
}

export function isDatetimeAttribute (object: any): object is DatetimeAttribute {
    return (
        isAttribute(object) && object.attributeValueType === AttributeValueType.DATETIME
    )
}

export function isMeasurementAttribute (object: any): object is MeasurementAttribute {
    return (
        isAttribute(object) && object.attributeValueType === AttributeValueType.MEASUREMENT
    )
}

export function isNumericAttribute (object: any): object is NumericAttribute {
    return (
        isAttribute(object) && object.attributeValueType === AttributeValueType.NUMERIC
    )
}

export function isCodeAttribute (object: any): object is CodeAttribute {
    return (
        isAttribute(object) && object.attributeValueType === AttributeValueType.CODE
    )
}

export function IsObjectAttribute (object: any): object is ObjectAttribute {
    return (
        isAttribute(object) && object.attributeValueType === AttributeValueType.OBJECT
    )
}

export function IsListAttribute (object: any): object is ListAttribute {
    return (
        isAttribute(object) && object.attributeValueType === AttributeValueType.LIST
    )
}
