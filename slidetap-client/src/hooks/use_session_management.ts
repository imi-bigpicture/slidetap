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
 * Important: The backend automatically refreshes the session on EVERY authenticated
 * API call. This means:
 * - Active users (making API requests) will never be timed out
 * - The timeout dialog only appears after genuine inactivity (no API calls)
 * - No explicit keepAlive polling is needed
 *
 * This hook checks session status every minute to detect when the session is
 * expiring soon (< 5 minutes remaining) and shows a warning dialog.
 */

import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import loginApi from 'src/services/api/login_api'

interface SessionManagementState {
  sessionExpiration: number | null
  timeRemaining: number
  isExpiringSoon: boolean
  showWarning: boolean
  extendSession: () => void
  dismissWarning: () => void
}

const WARNING_THRESHOLD_MINUTES = 5 // Show warning when < 5 minutes remaining

function getTimeRemaining(expirationTimestamp: number): number {
  const now = Math.floor(Date.now() / 1000)
  const remaining = expirationTimestamp - now
  return Math.max(0, remaining)
}

export function useSessionManagement(): SessionManagementState {
  const [sessionExpiration, setSessionExpiration] = useState<number | null>(null)
  const [timeRemaining, setTimeRemaining] = useState<number>(0)
  const [showWarning, setShowWarning] = useState<boolean>(false)

  // Fetch session status
  const sessionQuery = useQuery({
    queryKey: ['sessionStatus'],
    queryFn: async () => {
      return await loginApi.getSessionStatus()
    },
    refetchInterval: 60 * 1000, // Check every minute
    retry: 1,
  })

  // Update session expiration when query data changes
  useEffect(() => {
    if (sessionQuery.data?.exp) {
      setSessionExpiration(sessionQuery.data.exp)
    }
  }, [sessionQuery.data])

  // Update time remaining every second
  useEffect(() => {
    if (sessionExpiration === null) {
      return
    }

    const updateTimer = (): void => {
      const remaining = getTimeRemaining(sessionExpiration)
      setTimeRemaining(remaining)

      const thresholdSeconds = WARNING_THRESHOLD_MINUTES * 60
      if (remaining > 0 && remaining <= thresholdSeconds && !showWarning) {
        setShowWarning(true)
      }

      if (remaining === 0) {
        // Session expired - will be handled by 401 response
        setShowWarning(false)
      }
    }

    // Update immediately
    updateTimer()

    // Then update every second
    const interval = setInterval(updateTimer, 1000)

    return () => {
      clearInterval(interval)
    }
  }, [sessionExpiration, showWarning])

  const extendSession = (): void => {
    loginApi
      .keepAlive()
      .then(() => {
        // Refetch session status to get new expiration
        sessionQuery.refetch().catch((error) => {
          console.error('Failed to refetch session status:', error)
        })
        setShowWarning(false)
      })
      .catch((error) => {
        console.error('Failed to extend session:', error)
      })
  }

  const dismissWarning = (): void => {
    setShowWarning(false)
  }

  const isExpiringSoon =
    timeRemaining > 0 && timeRemaining <= WARNING_THRESHOLD_MINUTES * 60

  return {
    sessionExpiration,
    timeRemaining,
    isExpiringSoon,
    showWarning,
    extendSession,
    dismissWarning,
  }
}
