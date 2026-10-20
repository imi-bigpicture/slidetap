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
 * Session Management Hook
 *
 * Monitors user session expiration and provides warnings before timeout.
 *
 * The session is extended only by keep alives: periodically while the user is
 * active (see usePeriodicKeepAlive) or when the user extends it from the
 * warning. The session status is checked every minute, and the warning shown
 * when the session expires within five minutes, or within one keep alive
 * interval if that is shorter, so that a session kept alive more often than
 * every five minutes does not warn while it is in use.
 */

import { useEffect, useState } from 'react'
import {
  DEFAULT_KEEP_ALIVE_INTERVAL_SECONDS,
  useSessionStatus,
} from 'src/hooks/use_session_status'
import loginApi from 'src/services/api/login_api'

interface SessionManagementState {
  sessionExpiration: number | null
  timeRemaining: number
  isExpiringSoon: boolean
  showWarning: boolean
  extendSession: () => void
  dismissWarning: () => void
}

const WARNING_THRESHOLD_SECONDS = 5 * 60

function getTimeRemaining(expirationTimestamp: number): number {
  const now = Math.floor(Date.now() / 1000)
  const remaining = expirationTimestamp - now
  return Math.max(0, remaining)
}

export function useSessionManagement(): SessionManagementState {
  const [sessionExpiration, setSessionExpiration] = useState<number | null>(null)
  const [timeRemaining, setTimeRemaining] = useState<number>(0)
  /** The expiration the warning was dismissed or extended for. The warning
   * comes back only for a later expiration, not on the next tick. */
  const [handledExpiration, setHandledExpiration] = useState<number | null>(null)

  const sessionQuery = useSessionStatus()
  const warningThresholdSeconds = Math.min(
    WARNING_THRESHOLD_SECONDS,
    sessionQuery.data?.keep_alive_interval_seconds ?? DEFAULT_KEEP_ALIVE_INTERVAL_SECONDS,
  )

  // Follow the expiration the session status gives, keeping the last one known
  // while there is none
  const latestExpiration = sessionQuery.data?.exp
  if (latestExpiration && latestExpiration !== sessionExpiration) {
    setSessionExpiration(latestExpiration)
  }

  // Update time remaining every second
  useEffect(() => {
    if (sessionExpiration === null) {
      return
    }

    // Once expired, the warning is no longer shown: the next request is
    // turned away as unauthenticated and that leads to the login page.
    const updateTimer = (): void => {
      setTimeRemaining(getTimeRemaining(sessionExpiration))
    }

    // Update immediately
    updateTimer()

    // Then update every second
    const interval = setInterval(updateTimer, 1000)

    return () => {
      clearInterval(interval)
    }
  }, [sessionExpiration])

  const extendSession = (): void => {
    loginApi
      .keepAlive()
      .then(() => {
        // Refetch session status to get new expiration
        sessionQuery.refetch().catch((error) => {
          console.error('Failed to refetch session status:', error)
        })
        setHandledExpiration(sessionExpiration)
      })
      .catch((error) => {
        console.error('Failed to extend session:', error)
      })
  }

  const dismissWarning = (): void => {
    setHandledExpiration(sessionExpiration)
  }

  const isExpiringSoon =
    timeRemaining > 0 && timeRemaining <= warningThresholdSeconds
  const showWarning = isExpiringSoon && handledExpiration !== sessionExpiration

  return {
    sessionExpiration,
    timeRemaining,
    isExpiringSoon,
    showWarning,
    extendSession,
    dismissWarning,
  }
}
