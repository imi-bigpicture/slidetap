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

import type { Dzi } from 'src/models/dzi'
import type { Image } from 'src/models/item'
import type { Size } from 'src/models/setting'

import { get, parseJsonResponse } from 'src/services/api/api_methods'

const imageApi = {
  getImagesWithThumbnail: async (datasetUid: string, batchUid?: string) => {
    const query = new Map<string, string | undefined>([['batchUid', batchUid]])
    const response = await get('images/thumbnails/' + datasetUid, query)
    return await parseJsonResponse<Image[]>(response)
  },

  getThumbnail: async (imageUid: string, size: Size) => {
    const path = 'images/image/' + imageUid + '/thumbnail'
    const args = new Map<string, string>()
    args.set('width', size.width.toString())
    args.set('height', size.height.toString())
    const response = await get(path, args)
    return await response.blob()
  },

  getDzi: async (imageUid: string) => {
    const response = await get('images/image/' + imageUid + '/dzi')
    return await parseJsonResponse<Dzi>(response)
  },

  getTile: async (
    _: string,
    imageUid: string,
    level: number,
    x: number,
    y: number,
    extension: string,
  ) => {
    const path =
      'images/image/' +
      imageUid +
      '/dzi/' +
      level.toString() +
      '/' +
      x.toString() +
      '_' +
      y.toString() +
      '.' +
      extension
    const response = await get(path)
    return await response.blob()
  },
}

export default imageApi
