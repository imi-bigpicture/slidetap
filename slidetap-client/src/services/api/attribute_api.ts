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

import type { Attribute, AttributeValueTypes } from 'src/models/attribute'

import { get, parseJsonResponse, post } from 'src/services/api/api_methods'

const attributeApi = {
  getAttribute: async (attributeUid: string) => {
    const response = await get(`attributes/attribute/${attributeUid}`)
    return await parseJsonResponse<Attribute<AttributeValueTypes>>(response)
  },

  updateAttribute: async (attribute: Attribute<AttributeValueTypes>) => {
    return await post(`attributes/attribute/${attribute.uid}`, attribute)
  },

  createAttribute: async (attribute: Attribute<AttributeValueTypes>) => {
    const response = await post(`attributes/create/${attribute.schemaUid}`, attribute)
    return await parseJsonResponse<Attribute<AttributeValueTypes>>(response)
  },

  getAttributesForSchema: async <Type extends Attribute<AttributeValueTypes>>(attributeSchemaUid: string) => {
    const response = await get(`attributes/schema/${attributeSchemaUid}`)
    return await parseJsonResponse<Type[]>(response)
  }
}

export default attributeApi
