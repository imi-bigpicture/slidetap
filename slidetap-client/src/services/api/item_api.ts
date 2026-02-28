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
import { ItemSelect } from 'src/models/item_select'
import { Preview } from 'src/models/preview'
import type { TableRequest } from 'src/models/table_item'

import { get, parseJsonResponse, post } from 'src/services/api/api_methods'

const itemApi = {
  get: async (itemUid: string) => {
    const response = await get(`items/item/${itemUid}`)
    return await parseJsonResponse<Item>(response)
  },

  select: async (itemUid: string, select: ItemSelect) => {
    return await post(`items/item/${itemUid}/select`, select)
  },

  save: async (item: Item) => {
    const response = await post(`items/item/${item.uid}`, item)
    return await parseJsonResponse<Item>(response)
  },

  add: async (item: Item) => {
    const response = await post("items/add", item)
    return await parseJsonResponse<Item>(response)
  },

  create: async (schemaUid: string, projectUid: string, batchUid: string) => {
    const query = new Map<string, string | undefined>([
      ["schemaUid", schemaUid],
      ['projectUid', projectUid],
      ['batchUid', batchUid]])
    const response = await post("items/create", query)
    return await parseJsonResponse<Item>(response)
  },

  copy: async (itemUid: string) => {
    const response = await post(`items/item/${itemUid}/copy`)
    return await parseJsonResponse<Item>(response)
  },

  getReferences: async (
    schemaUid: string,
    datasetUid: string,
    batchUid: string | null
  ) => {
    const query = new Map<string, string | null>([
      ["datasetUid", datasetUid],
      ['itemSchemaUid', schemaUid],
      ['batchUid', batchUid]])
    const response = await get("items/references", query)
    return await parseJsonResponse<Record<string, ItemReference>>(response)
  },

  getItems: async <Type extends Item> (
    schemaUid: string,
    datasetUid: string,
    batchUid?: string,
    request?: TableRequest
  ) => {
    const query = new Map<string, string | undefined>([
      ["datasetUid", datasetUid],
      ['itemSchemaUid', schemaUid],
      ['batchUid', batchUid]])
    const response = await post("items", request, query)
    return await parseJsonResponse<{ items: Type[], count: number }>(response)
  },

  getPreview: async (itemUid: string) => {
    const response = await get(`items/item/${itemUid}/preview`)
    return await parseJsonResponse<Preview>(response)
  },

  retry: async (imageUids: string[]) => {
    return await post(`items/retry`, imageUids)
  },

  getImagesForitem: async (itemUid: string, groupBySchemaUid: string, imageSchemaUid?: string) => {
    const query = new Map<string, string | undefined>([['groupBySchemaUid', groupBySchemaUid], ['imageSchemaUid', imageSchemaUid]])
    const response = await get(`items/item/${itemUid}/images`, query)
    return await parseJsonResponse<ImageGroup[]>(response)
  }
}

export default itemApi
