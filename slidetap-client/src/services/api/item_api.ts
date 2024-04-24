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

import type { ItemDetails, ItemPreview, ItemReference } from 'models/item'
import type { Item, TableRequest } from 'models/table_item'

import { get, post } from 'services/api/api_methods'

const itemApi = {
  get: async (itemUid: string) => {
    return await get(`item/${itemUid}`).then<ItemDetails>(
      async (response) => await response.json(),
    )
  },

  select: async (itemUid: string, value: boolean) => {
    return await post(`item/${itemUid}/select?value=${value.toString()}`)
  },

  save: async (item: ItemDetails) => {
    return await post(`item/${item.uid}`, item).then<ItemDetails>(
      async (response) => await response.json(),
    )
  },

  add: async (item: ItemDetails, projectUid: string) => {
    return await post(`item/add/${item.schema.uid}/project/${projectUid}`, item).then<ItemDetails>(
      async (response) => await response.json(),
    )
  },

  create: async (schemaUid: string, projectUid: string) => {
    return await post(`item/create/${schemaUid}/project/${projectUid}`).then<ItemDetails>(
      async (response) => await response.json(),
    )
  },

  copy: async (itemUid: string) => {
    return await post(`item/${itemUid}/copy`).then<ItemDetails>(
      async (response) => await response.json(),
    )
  },

  getReferences: async (schemaUid: string, projectUid: string) => {
    return await get(`item/schema/${schemaUid}/project/${projectUid}/references`).then<ItemReference[]>(
      async (response) => await response.json(),
    )
  },
  getItems: async <Type extends Item> (
    schemaUid: string,
    projectUid: string,
    request?: TableRequest) => {

    return await post(`item/schema/${schemaUid}/project/${projectUid}/items`, request)
      .then<{ items: Type[], count: number }>(
      async (response) => await response.json(),
    )
  },
  getPreview: async (itemUid: string) => {
    return await get(`item/${itemUid}/preview`).then<ItemPreview>(
      async (response) => await response.json(),
    )
  },
  retry: async (imageUids: string[]) => {
    return await post(`item/retry`, imageUids)
  },
}

export default itemApi
