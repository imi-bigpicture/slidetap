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

import React, { useState, type ReactElement } from 'react'
import { useNavigate } from 'react-router-dom'
import Button from '@mui/material/Button'
import Alert from '@mui/material/Alert'
import CircularProgress from '@mui/material/CircularProgress'
import Box from '@mui/material/Box'
import { post } from 'services/api/api_methods'
import SectraAuth from 'services/auth'

function Login(): ReactElement {
  const [loading, setLoading] = useState<boolean>(false)
  const [message, setMessage] = useState<string>('')
  const navigate = useNavigate()
  function handleLogIn(event: React.MouseEvent<HTMLElement>): void {
    setMessage('')
    setLoading(true)
    post('auth/login', undefined, false)
      .then(() => {
        SectraAuth.login()
        navigate('/')
        window.location.reload()
        setLoading(false)
      })
      .catch((error) => {
        setLoading(false)
        console.error(error)
        setMessage('Login failed')
      })
    event.preventDefault()
  }

  return (
    <Box sx={{ display: 'flex' }}>
      <div>
        <h1>Login</h1>
        <form className="login">
          <Button href="http://localhost:5001/api/auth/login" disabled={loading}>
            Login
          </Button>
          {loading && <CircularProgress />}
          {message !== '' && <Alert severity="error">{message}</Alert>}
        </form>
      </div>
    </Box>
  )
}

export default Login
