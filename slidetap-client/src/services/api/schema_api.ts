import type { AttributeSchema } from 'models/schema'

import { get } from 'services/api/api_methods'

const projectApi = {
  getAttributeSchemas: async (schemaUid: string) => {
    return await get(`schemas/attributes/${schemaUid}`).then<AttributeSchema[]>(
      async (response) => await response.json(),
    )
  },
}

export default projectApi
