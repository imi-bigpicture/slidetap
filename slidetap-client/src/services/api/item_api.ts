import type { Item } from 'models/items'

import { post, get } from 'services/api/api_methods'

const itemApi = {
  get: async (itemUid: string) => {
    return await get(`item/${itemUid}`).then<Item>(
      async (response) => await response.json(),
    )
  },

  select: async (itemUid: string, value: boolean) => {
    return await post(`item/${itemUid}/select?value=${value.toString()}`)
  },

  update: async (item: Item) => {
    return await post(`item/${item.uid}`, item)
  },
}

export default itemApi
