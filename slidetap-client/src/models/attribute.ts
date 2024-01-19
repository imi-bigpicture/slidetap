import type {
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
import type { ValueStatus } from './status'

export enum AttributeValueType {
  STRING = 1,
  DATETIME = 2,
  NUMERIC = 3,
  MEASUREMENT = 4,
  CODE = 5,
  ENUM = 6,
  BOOLEAN = 7,
  OBJECT = 8,
  LIST = 10,
  UNION = 11,
}

export enum DatetimeType {
  TIME = 1,
  DATE = 2,
  DATETIME = 3,
}

export interface Code {
  code: string
  scheme: string
  meaning: string
  schemeVersion?: string
}

export interface Measurement {
  value: number
  unit: string
}

export interface Attribute<valueType, AttributeSchema> {
  /** Id of attribute. */
  uid: string
  /** Schema of attribute. */
  schema: AttributeSchema
  /** Display value of attribute, should summarize the attribute. */
  displayValue: string
  /** Value that can be used to map the attribute, if any. */
  mappableValue?: string
  /** Value of attribute. */
  value?: valueType
  /** If the attribute has been mapped or not etc. */
  mappingStatus: ValueStatus
  /** If the attribute has a valid value set. */
  valid: boolean
}

export interface StringAttribute extends Attribute<string, StringAttributeSchema> {}

export interface DatetimeAttribute extends Attribute<Date, DatetimeAttributeSchema> {}

export interface NumericAttribute extends Attribute<number, NumericAttributeSchema> {}

export interface MeasurementAttribute
  extends Attribute<Measurement, MeasurementAttributeSchema> {}

export interface CodeAttribute extends Attribute<Code, CodeAttributeSchema> {}

export interface EnumAttribute extends Attribute<string, EnumAttributeSchema> {}

export interface BooleanAttribute extends Attribute<boolean, BooleanAttributeSchema> {}

export interface ObjectAttribute
  extends Attribute<Record<string, Attribute<any, any>>, ObjectAttributeSchema> {}

export interface ListAttribute
  extends Attribute<Array<Attribute<any, any>>, ListAttributeSchema> {}

export interface UnionAttribute
  extends Attribute<Attribute<any, any>, UnionAttributeSchema> {}

export interface AttributeValidation {
  is_valid: boolean
}