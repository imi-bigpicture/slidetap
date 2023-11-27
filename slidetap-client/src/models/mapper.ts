import type { Attribute, AttributeValueType } from './attribute'

export interface Mapper {
  uid: string
  name: string
  schemaUid: string
  attributeSchemaUid: string
  attributeSchemaName: string
  attributeValueType: AttributeValueType
}

export interface MappingItem {
  uid: string
  mapperUid: string
  expression: string
  attribute: Attribute<any, any>
}
