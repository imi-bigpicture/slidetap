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
import { HierarchyNode } from 'src/models/hierarchy'
import { ItemIdentity } from 'src/models/item_identity'
import { ItemSelect } from 'src/models/item_select'
import type { OverviewRoot } from 'src/models/overview'
import { Preview } from 'src/models/preview'
import { ReviewQueueItem } from 'src/models/review_queue_item'
import { ReviewStatus } from 'src/models/review_status'
import type { TableRequest } from 'src/models/table_item'

import { get, parseJsonResponse, post } from 'src/services/api/api_methods'

const itemApi = {
  get: async (itemUid: string) => {
    const response = await get(`items/item/${itemUid}`)
    return await parseJsonResponse<Item>(response)
  },

  /** Move an item to a review status. Reviewing is what clears a flag; the
   * reason is written only when raising one. */
  setReviewStatus: async (itemUid: string, status: ReviewStatus, reason?: string) => {
    await post(`items/item/${itemUid}/review`, { status, reason: reason ?? null })
  },

  /** Flag every review unit holding something invalid. Asked for rather than
   * done on import: only the application knows when its items are supposed to
   * be valid. */
  flagInvalid: async (datasetUid: string, batchUid?: string) => {
    const query = new Map<string, string | undefined>([
      ['datasetUid', datasetUid],
      ['batchUid', batchUid],
    ])
    await post('items/flag-invalid', undefined, query)
  },

  select: async (itemUid: string, select: ItemSelect) => {
    return await post(`items/item/${itemUid}/select`, select)
  },

  save: async (item: Item) => {
    const response = await post(`items/item/${item.uid}`, item)
    return await parseJsonResponse<Item>(response)
  },

  add: async (item: Item) => {
    const response = await post('items/add', item)
    return await parseJsonResponse<Item>(response)
  },

  create: async (
    schemaUid: string,
    batchUid: string,
    targetParentUids?: string[],
    identifier?: string,
  ) => {
    const query = new Map<string, string | string[] | undefined>([
      ['schemaUid', schemaUid],
      ['batchUid', batchUid],
      ['targetParentUids', targetParentUids],
      ['identifier', identifier],
    ])
    const response = await post('items/create', undefined, query)
    return await parseJsonResponse<Item>(response)
  },

  copy: async (itemUid: string, targetParentUids?: string[], identifier?: string) => {
    const query = new Map<string, string | string[] | undefined>([
      ['targetParentUids', targetParentUids],
      ['identifier', identifier],
    ])
    const response = await post(`items/item/${itemUid}/copy`, undefined, query)
    return await parseJsonResponse<Item>(response)
  },

  /** What names the items of a schema, keyed by uid. */
  getIdentities: async (
    schemaUid: string,
    datasetUid: string,
    batchUid: string | null,
  ) => {
    const query = new Map<string, string | null>([
      ['datasetUid', datasetUid],
      ['itemSchemaUid', schemaUid],
      ['batchUid', batchUid],
    ])
    const response = await get('items/identities', query)
    const body = await parseJsonResponse<{ identities: Record<string, ItemIdentity> }>(
      response,
    )
    return body.identities
  },

  /** The items of a schema a reviewer works through. Without a status this is
   * all of them, so something nothing flagged can still be picked out. */
  getReviewQueue: async (
    schemaUid: string,
    datasetUid: string,
    batchUid: string | null,
    reviewStatus?: ReviewStatus,
  ) => {
    const query = new Map<string, string | null | undefined>([
      ['datasetUid', datasetUid],
      ['itemSchemaUid', schemaUid],
      ['batchUid', batchUid],
      ['reviewStatus', reviewStatus],
    ])
    const response = await get('items/review-queue', query)
    const body = await parseJsonResponse<{ items: ReviewQueueItem[] }>(response)
    return body.items
  },

  getItems: async <Type extends Item>(
    schemaUid: string,
    datasetUid: string,
    batchUid?: string,
    request?: TableRequest,
  ) => {
    const query = new Map<string, string | undefined>([
      ['datasetUid', datasetUid],
      ['itemSchemaUid', schemaUid],
      ['batchUid', batchUid],
    ])
    const response = await post('items', request, query)
    return await parseJsonResponse<{ items: Type[]; count: number }>(response)
  },

  /** What hangs under an item, as the layout asks for it. */
  getHierarchy: async (itemUid: string, hierarchyLayoutUid: string) => {
    const response = await get(`items/item/${itemUid}/hierarchy/${hierarchyLayoutUid}`)
    return await parseJsonResponse<HierarchyNode>(response)
  },

  getPreview: async (itemUid: string) => {
    const response = await get(`items/item/${itemUid}/preview`)
    return await parseJsonResponse<Preview>(response)
  },

  retry: async (imageUids: string[]) => {
    return await post(`items/retry`, imageUids)
  },

  remap: async (itemUid: string) => {
    return await post(`items/item/${itemUid}/remap`)
  },

  remapHierarchy: async (itemUid: string) => {
    return await post(`items/item/${itemUid}/remap_hierarchy`)
  },

  getImagesForitem: async (
    itemUid: string,
    groupBySchemaUid?: string,
    imagesLayoutUid?: string,
  ) => {
    const query = new Map<string, string | undefined>([
      ['groupBySchemaUid', groupBySchemaUid],
      ['imagesLayoutUid', imagesLayoutUid],
    ])
    const response = await get(`items/item/${itemUid}/images`, query)
    return await parseJsonResponse<ImageGroup[]>(response)
  },

  getOverviewRoot: async (
    itemUid: string,
    overviewLayoutUid: string,
    pseudonymMode: boolean,
    batchUid?: string,
    tableRequest?: TableRequest,
  ) => {
    const query = new Map<string, string | undefined>([
      ['pseudonymMode', String(pseudonymMode)],
      ['batchUid', batchUid],
    ])
    const response = tableRequest
      ? await post(
          `items/item/${itemUid}/overview/${overviewLayoutUid}`,
          tableRequest,
          query,
        )
      : await get(`items/item/${itemUid}/overview/${overviewLayoutUid}`, query)
    return await parseJsonResponse<OverviewRoot>(response)
  },

  /** Swap one attribute value between two existing items. Where no item exists
   * to swap with, move the whole item instead. */
  moveAttribute: async (
    sourceItemUid: string,
    attributeTag: string,
    targetItemUid: string,
  ) => {
    await post('items/move-attribute', {
      sourceItemUid,
      attributeTag,
      targetItemUid,
    })
  },

  /** Move an item to another parent, keeping the item and everything on it. */
  move: async (itemUid: string, targetParentUid: string) => {
    const query = new Map<string, string>([['targetParentUid', targetParentUid]])
    const response = await post(`items/item/${itemUid}/move`, undefined, query)
    return await parseJsonResponse<Item>(response)
  },
}

export default itemApi
