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

/**
 * Periodic Keep-Alive Hook
 *
 * Periodically calls the keep-alive endpoint to refresh the user session
 * while the user is actively using the application. This prevents session
 * timeout for active users.
 *
 * The hook:
 * - Checks as often as the session status asks (keep_alive_interval_seconds),
 *   which the server fits to how long the session lasts without a keep alive
 * - Only runs while the user is logged in, starting on login
 * - Calls keepAlive only if the user has used the page (pointer, keyboard or
 *   wheel) since the last check, so an idle session still times out
 * - Refetches the session status after a keep alive, so the expiration shown
 *   follows the new access token
 */

import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'
import { useIsLoggedIn } from 'src/hooks/use_is_logged_in'
import {
  DEFAULT_KEEP_ALIVE_INTERVAL_SECONDS,
  SESSION_STATUS_QUERY_KEY,
  useSessionStatus,
} from 'src/hooks/use_session_status'
import loginApi from 'src/services/api/login_api'

const ACTIVITY_EVENTS = ['pointerdown', 'keydown', 'wheel'] as const

export function usePeriodicKeepAlive(): void {
  const isLoggedIn = useIsLoggedIn()
  const queryClient = useQueryClient()
  const sessionQuery = useSessionStatus(isLoggedIn)
  const keepAliveIntervalSeconds =
    sessionQuery.data?.keep_alive_interval_seconds ??
    DEFAULT_KEEP_ALIVE_INTERVAL_SECONDS
  /** If the user has used the page since the last check. Kept outside the
   * interval, so that a changed interval does not forget activity. */
  const activeSinceLastCheck = useRef(false)

  useEffect(() => {
    if (!isLoggedIn) {
      return
    }
    const markActive = (): void => {
      activeSinceLastCheck.current = true
    }
    for (const eventName of ACTIVITY_EVENTS) {
      window.addEventListener(eventName, markActive, { passive: true })
    }
    return () => {
      for (const eventName of ACTIVITY_EVENTS) {
        window.removeEventListener(eventName, markActive)
      }
    }
  }, [isLoggedIn])

  useEffect(() => {
    if (!isLoggedIn) {
      return
    }
    const performKeepAlive = (): void => {
      if (!activeSinceLastCheck.current) {
        return
      }
      activeSinceLastCheck.current = false
      loginApi
        .keepAlive()
        .then(async () => {
          console.debug('Keep-alive successful')
          await queryClient.invalidateQueries({ queryKey: SESSION_STATUS_QUERY_KEY })
        })
        .catch((error) => {
          console.error('Keep-alive failed:', error)
          // If keep-alive fails (e.g., 401), the interceptor will handle logout
        })
    }
    const interval = setInterval(performKeepAlive, keepAliveIntervalSeconds * 1000)
    return () => {
      clearInterval(interval)
    }
  }, [isLoggedIn, keepAliveIntervalSeconds, queryClient])
}
