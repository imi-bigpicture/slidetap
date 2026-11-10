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

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useAllowsBatchExport } from 'src/hooks/use_allows_batch_export'
import applicationApi from 'src/services/api/application_api'

vi.mock('src/services/api/application_api', () => ({
  default: { getPolicy: vi.fn() },
}))

function renderAllowsBatchExport(queryClient: QueryClient) {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
  return renderHook(() => useAllowsBatchExport(), { wrapper })
}

describe('useAllowsBatchExport', () => {
  afterEach(() => {
    vi.resetAllMocks()
  })

  it('follows the server', async () => {
    // Arrange
    vi.mocked(applicationApi.getPolicy).mockResolvedValue({
      preProcessesImagesSeparately: true,
      allowsBatchExport: true,
    })

    // Act
    const { result } = renderAllowsBatchExport(new QueryClient())

    // Assert
    await waitFor(() => expect(result.current).toBe(true))
  })

  it('does not export batches alone until the server has said', () => {
    // Arrange
    vi.mocked(applicationApi.getPolicy).mockReturnValue(new Promise(() => {}))

    // Act
    const { result } = renderAllowsBatchExport(new QueryClient())

    // Assert
    expect(result.current).toBe(false)
  })

  it('does not export batches alone where asking fails', async () => {
    // Arrange
    vi.mocked(applicationApi.getPolicy).mockRejectedValue(new Error('not found'))
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })

    // Act
    const { result } = renderAllowsBatchExport(queryClient)

    // Assert
    await waitFor(() =>
      expect(queryClient.getQueryState(['application', 'policy'])?.status).toBe(
        'error',
      ),
    )
    expect(result.current).toBe(false)
  })
})
