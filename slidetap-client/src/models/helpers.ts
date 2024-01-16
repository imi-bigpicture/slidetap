import type {
  Attribute,
  BooleanAttribute,
  Code,
  CodeAttribute,
  DatetimeAttribute,
  EnumAttribute,
  ListAttribute,
  MeasurementAttribute,
  NumericAttribute,
  ObjectAttribute,
  StringAttribute,
  UnionAttribute,
} from './attribute'
import { AttributeValueType } from './attribute'

import type { Image, Item, Observation, Sample } from './item'
import type {
  AttributeSchema,
  BooleanAttributeSchema,
  CodeAttributeSchema,
  DatetimeAttributeSchema,
  EnumAttributeSchema,
  ListAttributeSchema,
  MeasurementAttributeSchema,
  NumericAttributeSchema,
  ObjectAttributeSchema,
  StringAttributeSchema,
  UnionAttributeSchema,
} from './schema'
import { ItemType } from './schema'


export function isCode(object: any): object is Code {
  return object != null && 'code' in object && 'scheme' in object && 'meaning' in object
}

export function isAttributeSchema(object: any): object is AttributeSchema {
  return object != null && 'schemaUid' in object && 'attributeValueType' in object
}

export function isStringAttributeSchema(object: any): object is StringAttributeSchema {
  return (
    isAttributeSchema(object) &&
    object.attributeValueType === AttributeValueType.STRING
  )
}

export function isDatetimeAttributeSchema (
  object: any
): object is DatetimeAttributeSchema {
  return (
    isAttributeSchema(object) &&
    object.attributeValueType === AttributeValueType.DATETIME
  )
}

export function isNumericAttributeSchema (
  object: any
): object is NumericAttributeSchema {
  return (
    isAttributeSchema(object) &&
    object.attributeValueType === AttributeValueType.NUMERIC
  )
}

export function isMeasurementAttributeSchema (
  object: any
): object is MeasurementAttributeSchema {
  return (
    isAttributeSchema(object) &&
    object.attributeValueType === AttributeValueType.MEASUREMENT
  )
}

export function isCodeAttributeSchema(object: any): object is CodeAttributeSchema {
  return (
    isAttributeSchema(object) && object.attributeValueType === AttributeValueType.CODE
  )
}

export function isEnumAttributeSchema(object: any): object is EnumAttributeSchema {
  return (
    isAttributeSchema(object) && object.attributeValueType === AttributeValueType.ENUM
  )
}

export function isBooleanAttributeSchema (
  object: any
): object is BooleanAttributeSchema {
  return (
    isAttributeSchema(object) &&
    object.attributeValueType === AttributeValueType.BOOLEAN
  )
}

export function isObjectAttributeSchema(object: any): object is ObjectAttributeSchema {
  return (
    isAttributeSchema(object) &&
    object.attributeValueType === AttributeValueType.OBJECT
  )
}

export function isListAttributeSchema(object: any): object is ListAttributeSchema {
  return (
    isAttributeSchema(object) && object.attributeValueType === AttributeValueType.LIST
  )
}

export function isUnionAttributeSchema(object: any): object is UnionAttributeSchema {
  return (
    isAttributeSchema(object) && object.attributeValueType === AttributeValueType.UNION
  )
}


export function isAttribute(object: any): object is Attribute<any, any> {
  return object != null && 'schema' in object && isAttributeSchema(object.schema)
}

export function isStringAttribute(object: any): object is StringAttribute {
  return (
    isAttribute(object) &&
    isStringAttributeSchema(object.schema)
  )
}

export function isDatetimeAttribute(object: any): object is DatetimeAttribute {
  return (
    isAttribute(object) &&
    isDatetimeAttributeSchema(object.schema)
  )
}

export function isNumericAttribute(object: any): object is NumericAttribute {
  return (
    isAttribute(object) &&
    isNumericAttributeSchema(object.schema)
    )
}

export function isMeasurementAttribute(object: any): object is MeasurementAttribute {
  return (
    isAttribute(object) &&
    isMeasurementAttributeSchema(object.schema)
  )
}

export function isCodeAttribute(object: any): object is CodeAttribute {
  return (
    isAttribute(object) && isCodeAttributeSchema(object.schema)
  )
}

export function isEnumAttribute(object: any): object is EnumAttribute {
  return (
    isAttribute(object) && isEnumAttributeSchema(object.schema)
  )
}

export function isBooleanAttribute(object: any): object is BooleanAttribute {
  return (
    isAttribute(object) &&
    isBooleanAttributeSchema(object.schema)
  )
}

export function isObjectAttribute(object: any): object is ObjectAttribute {
  return (
    isAttribute(object) &&
    isObjectAttributeSchema(object.schema)
  )
}

export function isListAttribute(object: any): object is ListAttribute {
  return (
    isAttribute(object) && isListAttributeSchema(object.schema)
  )
}

export function isUnionAttribute(object: any): object is UnionAttribute {
  return (
    isAttribute(object) && isUnionAttributeSchema(object.schema)
  )
}



export function isItem(object: any): object is Item {
  return object != null && 'itemValueType' in object
}

export function isSampleItem(object: any): object is Sample {
  return isItem(object) && object.itemValueType === ItemType.SAMPLE
}

export function isImageItem(object: any): object is Image {
  return isItem(object) && object.itemValueType === ItemType.IMAGE
}

export function isObservationItem(object: any): object is Observation {
  return isItem(object) && object.itemValueType === ItemType.OBSERVATION
}
