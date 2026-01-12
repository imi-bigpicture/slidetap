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

import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from '@mui/material'
import React from 'react'
import { useNavigate } from 'react-router-dom'
import { useSessionManagement } from 'src/hooks/use_session_management'
import auth from 'src/services/auth'

function formatTimeRemaining(seconds: number): string {
  const minutes = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${minutes}:${secs.toString().padStart(2, '0')}`
}

export default function SessionTimeoutDialog(): React.ReactElement {
  const sessionManagement = useSessionManagement()

  const navigate = useNavigate()

  const handleLogout = (): void => {
    auth.logout()
    navigate('/login')
    window.location.reload()
  }

  return (
    <Dialog
      open={sessionManagement.showWarning}
      onClose={sessionManagement.dismissWarning}
      aria-labelledby="session-timeout-dialog-title"
    >
      <DialogTitle id="session-timeout-dialog-title">Session Expiring Soon</DialogTitle>
      <DialogContent>
        <DialogContentText>
          Your session will expire in{' '}
          <strong>{formatTimeRemaining(sessionManagement.timeRemaining)}</strong>.
        </DialogContentText>
        <DialogContentText sx={{ mt: 2 }}>
          Would you like to extend your session?
        </DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleLogout} color="error">
          Logout
        </Button>
        <Button onClick={sessionManagement.dismissWarning}>Dismiss</Button>
        <Button onClick={sessionManagement.extendSession} variant="contained" autoFocus>
          Extend Session
        </Button>
      </DialogActions>
    </Dialog>
  )
}
