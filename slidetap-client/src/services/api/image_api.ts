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

import type { Dzi } from 'models/dzi'
import type { ImageDetails } from 'models/item'
import type { Size } from 'models/setting'

import { get } from 'services/api/api_methods'

const imageApi = {
  getImagesWithThumbnail: async (projectUid: string) => {
    return await get('image/thumbnails/' + projectUid).then<ImageDetails[]>(
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
