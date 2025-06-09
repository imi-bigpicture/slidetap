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
import { get } from 'src/services/api/api_methods'

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
    getItemSchema: async <T extends ItemSchema>(itemSchemaUid: string) => {
    return await get(`schema/item/${itemSchemaUid}`).then<T>(
      async (response) => await response.json(),
    )
    },
  // getDatasetSchema: async (DatasetSchemaUid: string) => {
  //   return await get(`schema/project/${DatasetSchemaUid}`).then<DatasetSchema>(
  //     async (response) => await response.json(),
  //   )
  // },
  getRootSchema: async () => {
    return await get('schema/root').then<RootSchema>(
      async (response) => await response.json(),
    )
  },
  getSchemaHierarchy: async (itemSchemaUid: string) => {
    return await get(`schema/item/${itemSchemaUid}/hierarchy`).then<ItemSchema[]>(
      async (response) => await response.json(),
    )
  },
}

export default schemaApi
