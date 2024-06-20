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

import type { Attribute } from 'models/attribute'
import type { AttributeValidation } from 'models/validation'

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
  getAttributesForSchema: async <Type extends Attribute<any, any>>(attributeSchemaUid: string) => {
    return await get(`attribute/schema/${attributeSchemaUid}`).then<
      Type[]
    >(async (response) => await response.json())
  },
  getValidation: async (attributeUid: string) => {
    return await get(`attribute/${attributeUid}/validation`).then<
      AttributeValidation
    >(async (response) => await response.json())
  }
}

export default attributeApi
