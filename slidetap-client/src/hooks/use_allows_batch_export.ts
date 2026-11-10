//    Copyright 2026 SECTRA AB
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

import { useQuery } from '@tanstack/react-query'
import applicationApi from 'src/services/api/application_api'
import { queryKeys } from 'src/services/query_keys'

/** Whether a locked batch can be exported on its own. False until the server
 * answers, and if the request fails. */
export function useAllowsBatchExport(): boolean {
  const policyQuery = useQuery({
    queryKey: queryKeys.application.policy(),
    queryFn: async () => await applicationApi.getPolicy(),
    // Fixed when the server starts, so never refetched.
    staleTime: Infinity,
  })
  return policyQuery.data?.allowsBatchExport ?? false
}
