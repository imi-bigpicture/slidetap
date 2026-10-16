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

import { MutationCache, QueryClient } from '@tanstack/react-query'
import { AuthenticationError } from 'src/services/api/api_methods'

/** The query client of the app, reporting a failed mutation with `showError`. */
export function createQueryClient(
  showError: (message: string, error?: unknown) => void,
): QueryClient {
  return new QueryClient({
    // A mutation that fails is shown to the user, unless it handles the error
    // itself: by an `onError` of its own, or by `meta: { handlesError: true }`
    // where it catches what `mutateAsync` throws. A request turned away as
    // unauthenticated is not reported, as it leads to the login page.
    mutationCache: new MutationCache({
      onError: (error, _variables, _context, mutation) => {
        if (
          mutation.options.onError !== undefined ||
          mutation.meta?.handlesError === true ||
          error instanceof AuthenticationError
        ) {
          return
        }
        const message = error instanceof Error ? error.message : 'Request failed'
        showError(message, error)
      },
    }),
    defaultOptions: {
      queries: {
        // A request turned away as unauthenticated is not tried again: it ends
        // the session, and the login page is shown instead.
        retry: (failureCount, error) =>
          !(error instanceof AuthenticationError) && failureCount < 1,
        refetchOnWindowFocus: false,
        staleTime: 30000,
      },
    },
  })
}
