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
 * - Checks every KEEPALIVE_INTERVAL_MS (default: 5 minutes)
 * - Only runs while the user is logged in, starting on login
 * - Calls keepAlive only if the user has used the page (pointer, keyboard or
 *   wheel) since the last check, so an idle session still times out
 */

import { useEffect, useRef } from 'react'
import { useIsLoggedIn } from 'src/hooks/use_is_logged_in'
import loginApi from 'src/services/api/login_api'

// Check for activity every 5 minutes
const KEEPALIVE_INTERVAL_MS = 5 * 60 * 1000

const ACTIVITY_EVENTS = ['pointerdown', 'keydown', 'wheel'] as const

export function usePeriodicKeepAlive(): void {
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const isLoggedIn = useIsLoggedIn()

  useEffect(() => {
    if (!isLoggedIn) {
      return
    }

    let activeSinceLastCheck = false
    const markActive = (): void => {
      activeSinceLastCheck = true
    }
    for (const eventName of ACTIVITY_EVENTS) {
      window.addEventListener(eventName, markActive, { passive: true })
    }

    const performKeepAlive = (): void => {
      if (!activeSinceLastCheck) {
        return
      }
      activeSinceLastCheck = false
      loginApi
        .keepAlive()
        .then(() => {
          console.debug('Keep-alive successful')
        })
        .catch((error) => {
          console.error('Keep-alive failed:', error)
          // If keep-alive fails (e.g., 401), the interceptor will handle logout
        })
    }

    // Start periodic keep-alive
    intervalRef.current = setInterval(performKeepAlive, KEEPALIVE_INTERVAL_MS)

    // Cleanup on unmount or when user logs out
    return () => {
      for (const eventName of ACTIVITY_EVENTS) {
        window.removeEventListener(eventName, markActive)
      }
      if (intervalRef.current !== null) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [isLoggedIn])

  // No return value needed - this hook just manages the side effect
}
