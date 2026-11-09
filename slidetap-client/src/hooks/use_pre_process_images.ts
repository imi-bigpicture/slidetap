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

/** Whether batches have a pre-processing step. Taken as having it until the
 * server has said, and where asking fails, as that is what every server
 * before the setting does. */
export function usePreProcessImages(): boolean {
  const policyQuery = useQuery({
    queryKey: queryKeys.application.policy(),
    queryFn: async () => await applicationApi.getPolicy(),
    // Set by the plugin when the server starts, so not asked again.
    staleTime: Infinity,
  })
  return policyQuery.data?.preProcessesImagesSeparately ?? true
}
