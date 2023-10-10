import React, { type ReactElement } from 'react'
import Button from '@mui/material/Button'
import { NavLink, useNavigate } from 'react-router-dom'

import loginApi from 'services/api/login_api'
import auth from 'services/auth'
import AppBar from '@mui/material/AppBar'
import Toolbar from '@mui/material/Toolbar'

export default function Header(): ReactElement {
  const navigate = useNavigate()
  function handleLogOut(event: React.MouseEvent<HTMLElement>): void {
    loginApi.logout().catch((x) => {
      console.error('Failed to log out due', x)
    })
    auth.logout()
    navigate('/')
    window.location.reload()
  }
  return (
    <React.Fragment>
      <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
        <Toolbar sx={{ justifyContent: 'space-between' }}>
          <div>
            <Button component={NavLink} to="/" color="inherit">
              SlideTap
            </Button>
            <Button
              component={NavLink}
              to="/project"
              color="inherit"
              sx={{ '&.active': { textDecoration: 'underline' } }}
            >
              Projects
            </Button>
            <Button
              component={NavLink}
              to="/mapping"
              color="inherit"
              sx={{ '&.active': { textDecoration: 'underline' } }}
            >
              Mappings
            </Button>
          </div>
          {auth.isLoggedIn() && (
            <Button onClick={handleLogOut} color="inherit">
              Log out
            </Button>
          )}
        </Toolbar>
      </AppBar>
      <Toolbar />
    </React.Fragment>
  )
}
