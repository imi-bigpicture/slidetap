//    Copyright 2024 SECTRA AB
//
//    Licensed under the Apache License, Version 2.0 (the "License");
//    you may not use this file except in compliance with the License.
//    You may obtain a copy of the License at
//
//        http://www.apache.org/licenses/LICENSE-2.0
//
//    Unless required by applicable law or agreed to in writing, software
//    distributed under the License is distributed on an "AS IS" BASIS,
//    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//    See the License for the specific language governing permissions and
//    limitations under the License.


import { AttributeSchema } from 'src/models/schema/attribute_schema'
import { ItemSchema } from 'src/models/schema/item_schema'
import { RootSchema } from 'src/models/schema/root_schema'
import { get, parseJsonResponse } from 'src/services/api/api_methods'

const schemaApi = {
  getAttributeSchemas: async () => {
    const response = await get(`schemas/attributes`)
    return await parseJsonResponse<AttributeSchema[]>(response)
  },

  getAttributeSchema: async (attributeSchemaUid: string) => {
    const response = await get(`schemas/attribute/${attributeSchemaUid}`)
    return await parseJsonResponse<AttributeSchema>(response)
  },

  getItemSchema: async <T extends ItemSchema>(itemSchemaUid: string) => {
    const response = await get(`schemas/item/${itemSchemaUid}`)
    return await parseJsonResponse<T>(response)
  },

  getRootSchema: async () => {
    const response = await get('schemas/root')
    return await parseJsonResponse<RootSchema>(response)
  },

  getSchemaHierarchy: async (itemSchemaUid: string) => {
    const response = await get(`schemas/item/${itemSchemaUid}/hierarchy`)
    return await parseJsonResponse<ItemSchema[]>(response)
  },
}

export default schemaApi
