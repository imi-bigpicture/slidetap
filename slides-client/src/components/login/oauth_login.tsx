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
