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

import type { ImageGroup, Item } from 'src/models/item'
import { ItemReference } from 'src/models/item_reference'
import type { TableRequest } from 'src/models/table_item'

import { get, post } from 'src/services/api/api_methods'

const itemApi = {
  get: async (itemUid: string) => {
    return await get(`items/item/${itemUid}`).then<Item>(
      async (response) => await response.json(),
    )
  },

  select: async (itemUid: string, value: boolean) => {
    return await post(`items/item/${itemUid}/select?value=${value.toString()}`)
  },

  save: async (item: Item) => {
    return await post(`items/item/${item.uid}`, item).then<Item>(
      async (response) => await response.json(),
    )
  },

  add: async (item: Item) => {
    return await post("items/add", item).then<Item>(
      async (response) => await response.json(),
    )
  },

  create: async (schemaUid: string, projectUid: string, batchUid: string) => {
    const query = new Map<string, string | undefined>([
      ["schemaUid", schemaUid],
      ['projectUid', projectUid],
      ['batchUid', batchUid]])
    return await post("items/create", query).then<Item>(
      async (response) => await response.json(),
    )
  },

  copy: async (itemUid: string) => {
    return await post(`items/item/${itemUid}/copy`).then<Item>(
      async (response) => await response.json(),
    )
  },

  getReferences: async (
    schemaUid: string,
    datasetUid: string,
    batchUid?: string,
  ) => {
    const query = new Map<string, string | undefined>([
      ["datasetUid", datasetUid],
      ['itemSchemaUid', schemaUid],
      ['batchUid', batchUid]])
    return await get("items/references", query).then<Record<string, ItemReference>>(
      async (response) => await response.json(),
    )
  },
  getItems: async <Type extends Item> (
    schemaUid: string,
    datasetUid: string,
    batchUid?: string,
    request?: TableRequest) => {
        const query = new Map<string, string | undefined>([
      ["datasetUid", datasetUid],
      ['itemSchemaUid', schemaUid],
      ['batchUid', batchUid]])
    return await post("items", request, query)
      .then<{ items: Type[], count: number }>(
      async (response) => await response.json(),
    )
  },
  getPreview: async (itemUid: string) => {
    return await get(`items/item/${itemUid}/preview`).then<string>(
      async (response) => await response.json(),
    )
  },
  retry: async (imageUids: string[]) => {
    return await post(`items/retry`, imageUids)
  },
  getImagesForitem: async (itemUid: string, groupBySchemaUid: string, imageSchemaUid?: string) => {
    const query = new Map<string, string | undefined>([['groupBySchemaUid', groupBySchemaUid], ['imageSchemaUid', imageSchemaUid]])
    return await get(`items/item/${itemUid}/images`, query).then<ImageGroup[]>(
      async (response) => await response.json(),
    )
  }
}

export default itemApi
