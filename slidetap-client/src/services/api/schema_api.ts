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
import { RootSchema, RootSchemaSummary } from 'src/models/schema/root_schema'
import { get, parseJsonResponse } from 'src/services/api/api_methods'

const schemaApi = {
  /** The attribute schemas of a root, or without one the root of new projects. */
  getAttributeSchemas: async (rootSchemaUid?: string) => {
    const response = await get(
      `schemas/attributes`,
      new Map([['rootSchemaUid', rootSchemaUid]]),
    )
    return await parseJsonResponse<AttributeSchema[]>(response)
  },

  getAttributeSchema: async (attributeSchemaUid: string) => {
    const response = await get(`schemas/attribute/${attributeSchemaUid}`)
    return await parseJsonResponse<AttributeSchema>(response)
  },

  /** An item schema of a root, or without one the root of new projects. */
  getItemSchema: async <T extends ItemSchema>(
    itemSchemaUid: string,
    rootSchemaUid?: string,
  ) => {
    const response = await get(
      `schemas/item/${itemSchemaUid}`,
      new Map([['rootSchemaUid', rootSchemaUid]]),
    )
    return await parseJsonResponse<T>(response)
  },

  /** The root schema of a project, or without one the root of new projects. */
  getRootSchema: async (rootSchemaUid?: string) => {
    const response = await get(
      rootSchemaUid === undefined ? 'schemas/root' : `schemas/root/${rootSchemaUid}`,
    )
    return await parseJsonResponse<RootSchema>(response)
  },

  /** The root schemas the application provides, and which of them new
   * projects are created with. */
  getRootSchemas: async () => {
    const response = await get('schemas/roots')
    return await parseJsonResponse<RootSchemaSummary[]>(response)
  },

  /** The hierarchy of an item schema of a root, or without one the root of new
   * projects. */
  getSchemaHierarchy: async (itemSchemaUid: string, rootSchemaUid?: string) => {
    const response = await get(
      `schemas/item/${itemSchemaUid}/hierarchy`,
      new Map([['rootSchemaUid', rootSchemaUid]]),
    )
    return await parseJsonResponse<ItemSchema[]>(response)
  },
}

export default schemaApi
