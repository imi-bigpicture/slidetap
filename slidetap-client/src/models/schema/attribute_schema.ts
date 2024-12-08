import { AttributeValueType } from "models/attribute_value_type"
import { DatetimeType } from "models/datetime_type"

export interface AttributeSchema {
    uid: string
    tag: string
    name: string
    displayName: string
    displayInTable: boolean
    optional: boolean
    readOnly: boolean
    attributeValueType: AttributeValueType
  }

  export interface StringAttributeSchema extends AttributeSchema {
    attributeValueType: AttributeValueType.STRING
  }

  export interface EnumAttributeSchema extends AttributeSchema {
    allowedValues: string[]
    attributeValueType: AttributeValueType.ENUM
  }

  export interface DatetimeAttributeSchema extends AttributeSchema {
    datetimeType: DatetimeType
    attributeValueType: AttributeValueType.DATETIME
  }

  export interface NumericAttributeSchema extends AttributeSchema {
    isInt: boolean
    attributeValueType: AttributeValueType.NUMERIC
  }

  export interface MeasurementAttributeSchema extends AttributeSchema {
    allowedUnits?: string[]
    attributeValueType: AttributeValueType.MEASUREMENT
  }

  export interface CodeAttributeSchema extends AttributeSchema {
    allowedSchemas?: string[]
    attributeValueType: AttributeValueType.CODE
  }

  export interface BooleanAttributeSchema extends AttributeSchema {
    trueDisplayValue: string
    falseDisplayValue: string
    attributeValueType: AttributeValueType.BOOLEAN
  }

  export interface ObjectAttributeSchema extends AttributeSchema {
    displayAttributesInParent: boolean
    attributes: Record<string, AttributeSchema>
    attributeValueType: AttributeValueType.OBJECT
  }

  export interface ListAttributeSchema extends AttributeSchema {
    displayAttributesInParent: boolean
    attribute: AttributeSchema
    attributeValueType: AttributeValueType.LIST
  }

  export interface UnionAttributeSchema extends AttributeSchema {
    attributes: Record<string, AttributeSchema>
    attributeValueType: AttributeValueType.UNION
  }
