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

import { TextField, Typography } from '@mui/material'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import CircularProgress from '@mui/material/CircularProgress'
import React, { useState, type ReactElement } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import loginApi from 'src/services/api/login_api'
import auth from 'src/services/auth'
import Header from '../header'

function BasicLogin(): ReactElement {
  const clearLogin = (): { username: string; password: string } => {
    return {
      username: '',
      password: '',
    }
  }

  const [loginForm, setLoginForm] = useState(clearLogin())
  const [loading, setLoading] = useState<boolean>(false)
  const [message, setMessage] = useState<string>('')
  const navigate = useNavigate()
  const location = useLocation()

  function handleLogIn(): void {
    setMessage('')
    setLoading(true)
    loginApi
      .login(loginForm.username, loginForm.password)
      .then(() => {
        auth.login()
        // Redirect to intended destination or default to '/'
        const from = (location.state as { from?: string })?.from || '/'
        navigate(from, { replace: true })
        setLoading(false)
        setLoginForm(clearLogin())
      })
      .catch((error) => {
        setLoading(false)
        console.error('Failed to login', error)
        setMessage('Login failed')
        setLoginForm({ ...loginForm, password: '' })
      })
  }

  function handleChange(event: React.ChangeEvent<HTMLInputElement>): void {
    const { value, name } = event.target
    setLoginForm((prevNote) => ({ ...prevNote, [name]: value }))
  }

  return (
    <React.Fragment>
      <Header />
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: 'calc(100vh - 64px)', // Subtract header height
        }}
      >
        <div>
          <Typography variant="h4" sx={{ mb: 2 }}>
            Login
          </Typography>
          <form
            className="login"
            onSubmit={(e) => {
              e.preventDefault()
              if (!loading) {
                handleLogIn()
              }
            }}
          >
            <TextField
              label="User name"
              name="username"
              type="text"
              variant="standard"
              required={true}
              onChange={handleChange}
              value={loginForm.username}
              autoFocus
              fullWidth
              sx={{ mb: 2 }}
            ></TextField>
            <TextField
              label="Password"
              name="password"
              type="password"
              variant="standard"
              required={true}
              onChange={handleChange}
              value={loginForm.password}
              fullWidth
              sx={{ mb: 2 }}
            ></TextField>
            <Button type="submit" disabled={loading} fullWidth>
              Login
            </Button>
            {loading && (
              <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
                <CircularProgress />
              </Box>
            )}
            {message !== '' && (
              <Alert severity="error" sx={{ mt: 2 }}>
                {message}
              </Alert>
            )}
          </form>
        </div>
      </Box>
    </React.Fragment>
  )
}

export default BasicLogin
