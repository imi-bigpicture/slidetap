import { AttributeValueType } from "src/models/attribute_value_type"
import { DatetimeType } from "src/models/datetime_type"

export interface AttributeSchema {
    uid: string
    tag: string
    name: string
    displayName: string
    displayInTable: boolean
    optional: boolean
    readOnly: boolean
    description: string | null
    attributeValueType: AttributeValueType
  }

  export interface StringAttributeSchema extends AttributeSchema {
    multiline: boolean
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
    minValue: number | null
    maxValue: number | null
    attributeValueType: AttributeValueType.NUMERIC
  }

  export interface MeasurementAttributeSchema extends AttributeSchema {
    allowedUnits: string[] | null
    minValue: number | null
    maxValue: number | null
    attributeValueType: AttributeValueType.MEASUREMENT
  }

  export interface CodeAttributeSchema extends AttributeSchema {
    allowedSchemas: string[] | null
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
    attributes: AttributeSchema[]
    attributeValueType: AttributeValueType.UNION
  }
