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
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import React, { useState, type ReactElement } from 'react'
import { useNavigate } from 'react-router-dom'
import loginApi from 'src/services/api/login_api'
import auth from 'src/services/auth'

function BasicLogin(): ReactElement {
  const clearLogin = (): { username: string; password: string } => {
    return {
      username: '',
      password: '',
    }
  }

  const [loginForm, setloginForm] = useState(clearLogin())
  const [loading, setLoading] = useState<boolean>(false)
  const [message, setMessage] = useState<string>('')
  const navigate = useNavigate()
  function handleLogIn(event: React.MouseEvent<HTMLElement>): void {
    setMessage('')
    setLoading(true)
    loginApi
      .login(loginForm.username, loginForm.password)
      .then(() => {
        auth.login()
        navigate('/')
        window.location.reload()
        setLoading(false)
      })
      .catch((error) => {
        setLoading(false)
        console.error('Failed to loging', error)
        setMessage('Login failed')
      })
    setloginForm(clearLogin())
    event.preventDefault()
  }

  function handleChange(event: React.ChangeEvent<HTMLInputElement>): void {
    const { value, name } = event.target
    setloginForm((prevNote) => ({ ...prevNote, [name]: value }))
  }

  useQuery({
    queryKey: ['keepAlive'],
    queryFn: () => {
      return auth.keepAlive()
    },
    refetchInterval: 30 * 1000,
    placeholderData: keepPreviousData,
  })

  return (
    <Box sx={{ display: 'flex' }}>
      <div>
        <Typography variant="h4">Login</Typography>
        <form className="login">
          <TextField
            label="User name"
            name="username"
            type="text"
            variant="standard"
            onChange={handleChange}
            value={loginForm.username}
            autoFocus
          ></TextField>
          <TextField
            label="Password"
            name="password"
            type="password"
            variant="standard"
            onChange={handleChange}
            value={loginForm.password}
          ></TextField>
          <Button onClick={handleLogIn} disabled={loading}>
            Login
          </Button>
          {loading && <CircularProgress />}
          {message !== '' && <Alert severity="error">{message}</Alert>}
        </form>
      </div>
    </Box>
  )
}

export default BasicLogin
