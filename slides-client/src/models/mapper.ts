import { Attribute, AttributeValueType } from "./attribute"

export interface Mapper {
    uid: string
    name: string
    schemaUid: string
    attributeSchemaUid: string
    attributeSchemaName: string
    attributeValueType: AttributeValueType
}

export interface Mapping {
    attributeUid: string
    mappableValue: string
    mapperName: string | null
    mapperUid: string | null
    expression: string | null
    valueUid: string | null
}

export interface MappingItem {
    uid: string
    expression: string
    value: Attribute<any, any>
}
