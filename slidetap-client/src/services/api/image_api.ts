import type { Dzi } from 'models/dzi'
import type { Image } from 'models/items'
import { Size } from 'models/setting'

import { get } from 'services/api/api_methods'

const imageApi = {
  getImagesWithThumbnail: async (projectUid: string) => {
    return await get('image/thumbnails/' + projectUid).then<Image[]>(
      async (response) => await response.json(),
    )
  },

  getThumbnail: async (imageUid: string, size: Size) => {
    const path = 'image/' + imageUid + '/thumbnail'
    const args = new Map<string, string>()
    args.set('width', size.width.toString())
    args.set('height', size.height.toString())
    return await get(path, args).then<Blob>(async (response) => await response.blob())
  },

  getDzi: async (imageUid: string) => {
    return await get('image/' + imageUid).then<Dzi>(
      async (response) => await response.json(),
    )
  },

  getTile: async (
    projectUid: string,
    imageUid: string,
    level: number,
    x: number,
    y: number,
    extension: string,
  ) => {
    const path =
      'image/' +
      imageUid +
      '/' +
      level.toString() +
      '/' +
      x.toString() +
      '_' +
      y.toString() +
      '.' +
      extension
    return await get(path).then<Blob>(async (response) => await response.blob())
  },
}

export default imageApi
