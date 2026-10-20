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

import { useQuery, type UseQueryResult } from '@tanstack/react-query'
import loginApi, { type SessionStatus } from 'src/services/api/login_api'

export const SESSION_STATUS_QUERY_KEY = ['sessionStatus']

/** Keep alive interval to use until the session status has given one. */
export const DEFAULT_KEEP_ALIVE_INTERVAL_SECONDS = 5 * 60

/**
 * The status of the logged in session, checked every minute.
 *
 * The status gives when the access token expires and how often to send a
 * keep alive while logged in.
 */
export function useSessionStatus(enabled = true): UseQueryResult<SessionStatus> {
  return useQuery({
    queryKey: SESSION_STATUS_QUERY_KEY,
    queryFn: async () => {
      return await loginApi.getSessionStatus()
    },
    refetchInterval: 60 * 1000,
    retry: 1,
    enabled,
  })
}
