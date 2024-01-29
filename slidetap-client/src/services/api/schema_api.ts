import type { AttributeSchema, ItemSchema } from 'models/schema'

import { get } from 'services/api/api_methods'

const schemaApi = {
  getAttributeSchemas: async (schemaUid: string) => {
    return await get(`schema/attributes/${schemaUid}`).then<AttributeSchema[]>(
      async (response) => await response.json(),
    )
  },
  getAttributeSchema: async (attributeSchemaUid: string) => {
    return await get(`schema/attribute/${attributeSchemaUid}`).then<AttributeSchema>(
      async (response) => await response.json(),
    )
  },
  getItemSchemas: async (schemaUid: string) => {
    return await get(`schema/items/${schemaUid}`).then<ItemSchema[]>(
      async (response) => await response.json(),
    )
  },
  getItemSchema: async (itemSchemaUid: string) => {
    return await get(`schema/item/${itemSchemaUid}`).then<ItemSchema>(
      async (response) => await response.json(),
    )
  },
}

export default schemaApi
