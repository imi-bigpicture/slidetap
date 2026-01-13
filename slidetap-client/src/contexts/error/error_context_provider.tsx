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

import { Alert, Snackbar } from '@mui/material'
import React, { useState, type ReactNode } from 'react'
import { ErrorContext } from './error_context'

type ErrorSeverity = 'error' | 'warning' | 'info' | 'success'

interface ErrorNotification {
  message: string
  severity: ErrorSeverity
}

interface ErrorProviderProps {
  children: ReactNode
}

export function ErrorProvider({ children }: ErrorProviderProps): React.ReactElement {
  const [notification, setNotification] = useState<ErrorNotification | null>(null)
  const [open, setOpen] = useState(false)

  const showNotification = (
    message: string,
    severity: ErrorSeverity,
    error?: unknown,
  ): void => {
    setNotification({ message, severity })
    setOpen(true)

    // Log errors to console for debugging (warnings/errors only)
    if (error && (severity === 'error' || severity === 'warning')) {
      console.error(`[${severity.toUpperCase()}] ${message}`, error)
    }
  }

  const showError = (message: string, error?: unknown): void => {
    showNotification(message, 'error', error)
  }

  const showWarning = (message: string, error?: unknown): void => {
    showNotification(message, 'warning', error)
  }

  const showInfo = (message: string, error?: unknown): void => {
    showNotification(message, 'info', error)
  }

  const showSuccess = (message: string, error?: unknown): void => {
    showNotification(message, 'success', error)
  }

  const handleClose = (
    _event?: React.SyntheticEvent | Event,
    reason?: string,
  ): void => {
    if (reason === 'clickaway') {
      return
    }
    setOpen(false)
  }

  return (
    <ErrorContext.Provider value={{ showError, showWarning, showInfo, showSuccess }}>
      {children}
      <Snackbar
        open={open}
        autoHideDuration={6000}
        onClose={handleClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={handleClose}
          severity={notification?.severity}
          sx={{ width: '100%' }}
        >
          {notification?.message}
        </Alert>
      </Snackbar>
    </ErrorContext.Provider>
  )
}
