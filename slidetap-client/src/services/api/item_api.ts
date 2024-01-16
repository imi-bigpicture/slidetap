import type { Item, ItemReference } from 'models/items'

import { get, post } from 'services/api/api_methods'

const itemApi = {
  get: async (itemUid: string) => {
    return await get(`item/${itemUid}`).then<Item>(
      async (response) => await response.json(),
    )
  },

  select: async (itemUid: string, value: boolean) => {
    return await post(`item/${itemUid}/select?value=${value.toString()}`)
  },

  save: async (item: Item) => {
    return await post(`item/${item.uid}`, item).then<Item>(
      async (response) => await response.json(),
    )
  },

  add: async (item: Item, projectUid: string) => {
    return await post(`item/add/${item.schema.uid}/project/${projectUid}`, item).then<Item>(
      async (response) => await response.json(),
    )
  },

  create: async (schemaUid: string, projectUid: string) => {
    return await post(`item/create/${schemaUid}/project/${projectUid}`).then<Item>(
      async (response) => await response.json(),
    )
  },

  copy: async (itemUid: string) => {
    return await post(`item/${itemUid}/copy`).then<Item>(
      async (response) => await response.json(),
    )
  },

  getOfSchema: async (schemaUid: string, projectUid: string) => {
    return await get(`item/schema/${schemaUid}/project/${projectUid}`).then<ItemReference[]>(
      async (response) => await response.json(),
    )
  },
  getPreview: async (itemUid: string) => {
    return await get(`item/${itemUid}/preview`).then<string>(
      async (response) => await response.text(),
    )
  }
}

export default itemApi
