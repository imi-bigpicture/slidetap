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

import Button from '@mui/material/Button'
import React, { type ReactElement } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'

import AppBar from '@mui/material/AppBar'
import Toolbar from '@mui/material/Toolbar'
import loginApi from 'src/services/api/login_api'
import auth from 'src/services/auth'

export default function Header(): ReactElement {
  const navigate = useNavigate()
  function handleLogOut(): void {
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
            {/* <Button
              component={NavLink}
              to="/dataset"
              color="inherit"
              sx={{ '&.active': { textDecoration: 'underline' } }}
            >
              Datasets
            </Button> */}
            <Button
              component={NavLink}
              to="/mapping"
              color="inherit"
              sx={{ '&.active': { textDecoration: 'underline' } }}
            >
              Mappings
            </Button>
            <Button
              component={NavLink}
              to="/schemas"
              color="inherit"
              sx={{ '&.active': { textDecoration: 'underline' } }}
            >
              Schemas
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
