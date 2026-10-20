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

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { usePeriodicKeepAlive } from 'src/hooks/use_periodic_keepalive'
import loginApi from 'src/services/api/login_api'

vi.mock('src/services/api/login_api', () => ({
  default: { getSessionStatus: vi.fn(), keepAlive: vi.fn() },
}))

vi.mock('src/hooks/use_is_logged_in', () => ({
  useIsLoggedIn: () => true,
}))

function renderPeriodicKeepAlive() {
  const queryClient = new QueryClient()
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
  return renderHook(() => usePeriodicKeepAlive(), { wrapper })
}

/** Lets the session status query settle, then moves time forward. */
async function advanceSeconds(seconds: number): Promise<void> {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(seconds * 1000)
  })
}

describe('usePeriodicKeepAlive', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.mocked(loginApi.getSessionStatus).mockResolvedValue({
      exp: Math.floor(Date.now() / 1000) + 300,
      user: 'user',
      keep_alive_interval_seconds: 100,
    })
    vi.mocked(loginApi.keepAlive).mockResolvedValue(new Response())
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.resetAllMocks()
  })

  it('renews the login of an active user at the interval the session status gives', async () => {
    // Arrange
    renderPeriodicKeepAlive()
    await advanceSeconds(1)

    // Act
    window.dispatchEvent(new Event('pointerdown'))
    await advanceSeconds(100)

    // Assert
    expect(loginApi.keepAlive).toHaveBeenCalledTimes(1)
    expect(loginApi.keepAlive).toHaveBeenCalledWith(true)
  })

  it('keeps the session of an idle user alive without renewing the login', async () => {
    // Arrange
    renderPeriodicKeepAlive()

    // Act
    await advanceSeconds(301)

    // Assert
    expect(loginApi.keepAlive).toHaveBeenCalledTimes(3)
    expect(loginApi.keepAlive).not.toHaveBeenCalledWith(true)
  })

  it('tells only the first keep alive after activity that the user was active', async () => {
    // Arrange
    renderPeriodicKeepAlive()
    await advanceSeconds(1)
    window.dispatchEvent(new Event('keydown'))

    // Act
    await advanceSeconds(200)

    // Assert
    expect(vi.mocked(loginApi.keepAlive).mock.calls).toEqual([[true], [false]])
  })
})
