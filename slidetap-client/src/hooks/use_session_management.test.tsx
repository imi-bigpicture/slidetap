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
import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useSessionManagement } from 'src/hooks/use_session_management'
import loginApi from 'src/services/api/login_api'

vi.mock('src/services/api/login_api', () => ({
  default: { getSessionStatus: vi.fn(), keepAlive: vi.fn() },
}))

/** An expiration `seconds` from now, as the session status gives it. */
function expiresIn(seconds: number): number {
  return Math.floor(Date.now() / 1000) + seconds
}

function renderSessionManagement(queryClient: QueryClient) {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
  return renderHook(() => useSessionManagement(), { wrapper })
}

describe('useSessionManagement', () => {
  afterEach(() => {
    vi.resetAllMocks()
  })

  it('warns of a session expiring soon', async () => {
    // Arrange
    vi.mocked(loginApi.getSessionStatus).mockResolvedValue({
      exp: expiresIn(120),
      user: 'user',
    })

    // Act
    const { result } = renderSessionManagement(new QueryClient())

    // Assert
    await waitFor(() => expect(result.current.showWarning).toBe(true))
  })

  it('does not warn of a session with time left', async () => {
    // Arrange
    vi.mocked(loginApi.getSessionStatus).mockResolvedValue({
      exp: expiresIn(3600),
      user: 'user',
    })

    // Act
    const { result } = renderSessionManagement(new QueryClient())

    // Assert
    await waitFor(() => expect(result.current.sessionExpiration).not.toBeNull())
    expect(result.current.showWarning).toBe(false)
  })

  it('keeps a dismissed warning away for the same expiration', async () => {
    // Arrange
    const expiration = expiresIn(120)
    vi.mocked(loginApi.getSessionStatus).mockResolvedValue({
      exp: expiration,
      user: 'user',
    })
    const queryClient = new QueryClient()
    const { result } = renderSessionManagement(queryClient)
    await waitFor(() => expect(result.current.showWarning).toBe(true))

    // Act
    act(() => result.current.dismissWarning())
    act(() => queryClient.setQueryData(['sessionStatus'], { exp: expiration, user: 'user' }))

    // Assert
    expect(result.current.isExpiringSoon).toBe(true)
    expect(result.current.showWarning).toBe(false)
  })

  it('warns again for a later expiration after a dismissal', async () => {
    // Arrange
    vi.mocked(loginApi.getSessionStatus).mockResolvedValue({
      exp: expiresIn(120),
      user: 'user',
    })
    const queryClient = new QueryClient()
    const { result } = renderSessionManagement(queryClient)
    await waitFor(() => expect(result.current.showWarning).toBe(true))
    act(() => result.current.dismissWarning())

    // Act
    act(() => queryClient.setQueryData(['sessionStatus'], { exp: expiresIn(180), user: 'user' }))

    // Assert
    await waitFor(() => expect(result.current.showWarning).toBe(true))
  })
})
