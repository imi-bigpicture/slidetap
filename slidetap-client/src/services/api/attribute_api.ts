import type { Attribute } from 'models/attribute'

import { get, post } from 'services/api/api_methods'

const attributeApi = {
  getAttribute: async (attributeUid: string) => {
    return await get(`attribute/${attributeUid}`).then<Attribute<any, any>>(
      async (response) => await response.json(),
    )
  },

  updateAttribute: async (attribute: Attribute<any, any>) => {
    return await post(`attribute/${attribute.uid}/update`, attribute)
  },

  createAttribute: async (attribute: Attribute<any, any>) => {
    return await post(`create/${attribute.schema.uid}/create`, attribute).then<
      Attribute<any, any>
    >(async (response) => await response.json())
  },

  getAttributesForSchema: async <Type>(attributeSchemaUid: string) => {
    return await get(`attribute/schema/${attributeSchemaUid}`).then<
      Type[]
    >(async (response) => await response.json())
  },
}

export default attributeApi
