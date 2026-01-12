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

import { get, parseJsonResponse, post } from 'src/services/api/api_methods'

export interface SessionStatus {
  exp: number
  user: string
}

const loginApi = {
  login: async (username: string, password: string) => {
    return await post(
      'auth/login',
      {
        username,
        password,
      },
    )
  },

  logout: async () => {
    return await post('auth/logout')
  },

  keepAlive: async () => {
    return await post('auth/keepAlive')
  },

  getSessionStatus: async () => {
    const response = await get('auth/session_status')
    return await parseJsonResponse<SessionStatus>(response)
  },
}

export default loginApi
