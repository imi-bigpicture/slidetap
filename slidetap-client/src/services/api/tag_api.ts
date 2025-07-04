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

import { Tag } from 'src/models/tag'

import { get, post } from 'src/services/api/api_methods'

const tagApi = {

  getTags: async () => {
    const url = "tags"
    return await get(url).then<Tag[]>(
      async (response) => await response.json(),
    )
  },

  save: async (tag: Tag) => {
    const url = `tags/tag/${tag.uid}`
    return await post(url, tag).then<Tag>(
      async (response) => await response.json(),
    )
  }
}

export default tagApi
