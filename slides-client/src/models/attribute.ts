export enum AttributeValueType {
    STRING = 1,
    DATETIME = 2,
    NUMERIC = 3,
    MEASUREMENT = 4,
    CODE = 5,
    BOOLEAN = 7,
    OBJECT = 8,
    LIST = 10,
}

export enum DatetimeType {
    TIME = 1,
    DATE = 2,
    DATETIME = 3
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
export interface Attribute<type> {
    uid: string
    tag: string
    value: type
    schemaDisplayName: string
    schemaUid: string
    displayValue: string | null
    attributeValueType: AttributeValueType
    mappableValue: string | null
}

export interface StringAttribute extends Attribute<string> {
    allowedValues: string[]
}

export interface DatetimeAttribute extends Attribute<Date> {
    datetimeType: DatetimeType
}

export interface NumericAttribute extends Attribute<number> {
    isInteger: boolean
}

export interface MeasurementAttribute extends Attribute<number> {
    isInteger: boolean
    unit: string
}

export interface CodeAttribute extends Attribute<Code> {
    allowedSchemas: string[]
}
export interface ObjectAttribute extends Attribute<Record<string, Attribute<any>>> {
}

export interface ListAttribute extends Attribute<Array<Attribute<any>>> {
}
