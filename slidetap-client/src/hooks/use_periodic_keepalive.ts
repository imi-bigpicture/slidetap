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
 * - Calls keepAlive every KEEPALIVE_INTERVAL_MS (default: 5 minutes)
 * - Only runs when user is logged in
 * - Stops when user becomes inactive (optional)
 */

import { useEffect, useRef } from 'react'
import loginApi from 'src/services/api/login_api'
import auth from 'src/services/auth'

// Call keep-alive every 5 minutes
const KEEPALIVE_INTERVAL_MS = 5 * 60 * 1000

export function usePeriodicKeepAlive(): void {
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    // Only run if user is logged in
    if (!auth.isLoggedIn()) {
      return
    }

    const performKeepAlive = (): void => {
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
      if (intervalRef.current !== null) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, []) // Empty dependency array - only set up once

  // No return value needed - this hook just manages the side effect
}
