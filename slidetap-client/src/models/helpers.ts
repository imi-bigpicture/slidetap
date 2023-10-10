import {
  type Attribute,
  AttributeValueType,
  type CodeAttribute,
  type DatetimeAttribute,
  type MeasurementAttribute,
  type NumericAttribute,
  type StringAttribute,
  type ObjectAttribute,
  type ListAttribute,
  type EnumAttribute,
  type UnionAttribute,
  type BooleanAttribute,
} from './attribute'

export function isAttribute(object: any): object is Attribute<any, any> {
  return object != null && 'schema' in object && 'attributeValueType' in object.schema
}

export function isStringAttribute(object: any): object is StringAttribute {
  return (
    isAttribute(object) &&
    object.schema.attributeValueType === AttributeValueType.STRING
  )
}

export function isDatetimeAttribute(object: any): object is DatetimeAttribute {
  return (
    isAttribute(object) &&
    object.schema.attributeValueType === AttributeValueType.DATETIME
  )
}

export function isNumericAttribute(object: any): object is NumericAttribute {
  return (
    isAttribute(object) &&
    object.schema.attributeValueType === AttributeValueType.NUMERIC
  )
}

export function isMeasurementAttribute(object: any): object is MeasurementAttribute {
  return (
    isAttribute(object) &&
    object.schema.attributeValueType === AttributeValueType.MEASUREMENT
  )
}

export function isCodeAttribute(object: any): object is CodeAttribute {
  return (
    isAttribute(object) && object.schema.attributeValueType === AttributeValueType.CODE
  )
}

export function isEnumAttribute(object: any): object is EnumAttribute {
  return (
    isAttribute(object) && object.schema.attributeValueType === AttributeValueType.ENUM
  )
}

export function isBooleanAttribute(object: any): object is BooleanAttribute {
  return (
    isAttribute(object) &&
    object.schema.attributeValueType === AttributeValueType.BOOLEAN
  )
}

export function IsObjectAttribute(object: any): object is ObjectAttribute {
  return (
    isAttribute(object) &&
    object.schema.attributeValueType === AttributeValueType.OBJECT
  )
}

export function IsListAttribute(object: any): object is ListAttribute {
  return (
    isAttribute(object) && object.schema.attributeValueType === AttributeValueType.LIST
  )
}

export function IsUnionAttribute(object: any): object is UnionAttribute {
  return (
    isAttribute(object) && object.schema.attributeValueType === AttributeValueType.UNION
  )
}
