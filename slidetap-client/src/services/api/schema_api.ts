import type { AttributeSchema } from 'models/schema'

import { get } from 'services/api/api_methods'

const schemaApi = {
  getAttributeSchemas: async (schemaUid: string) => {
    return await get(`schema/attributes/${schemaUid}`).then<AttributeSchema[]>(
      async (response) => await response.json(),
    )
  },
}

export default schemaApi
