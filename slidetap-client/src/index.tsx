import React, { useEffect, type ReactElement } from 'react'
import { createRoot } from 'react-dom/client'
import { Route, BrowserRouter as Router, Routes } from 'react-router-dom'
import DisplayProjects from './components/project/display_projects'
import './index.css'
// import Login from './components/oauth_login'
import Login from './components/login/basic_login'

import { Box } from '@mui/system'
import DisplayMapper from 'components/mapper/display_mapper'
import DisplayMappers from 'components/mapper/display_mappers'
import DisplaySchemas from 'components/schema/display_schemas'
import Title from 'components/title'
import Header from './components/header'
import DisplayProject from './components/project/display_project'
import auth from './services/auth'

function App(): ReactElement {
  useEffect(() => {
    // TODO keep alive interval should be taken from login session
    const keepAliveInterval = 30 * 1000
    const interval = setInterval(() => {
      auth.keepAlive()
    }, keepAliveInterval)
    return () => {
      clearInterval(interval)
    }
  })

  return (
    <React.StrictMode>
      <Router>
        <Header />
        <Box margin={0}>
          {!auth.isLoggedIn() ? (
            <Login />
          ) : (
            <Routes>
              <Route path="/" element={<Title />} />
              <Route path="/mapping" element={<DisplayMappers />} />
              <Route path="/mapping/:id/*" element={<DisplayMapper />} />
              <Route path="/project" element={<DisplayProjects />} />
              <Route path="/project/:id/*" element={<DisplayProject />} />
              <Route path="/schemas" element={<DisplaySchemas />} />
            </Routes>
          )}
        </Box>
      </Router>
    </React.StrictMode>
  )
}

const container = document.getElementById('root')
if (container !== null) {
  const root = createRoot(container)
  root.render(<App />)
} else {
  console.error('Failed to create react root.')
}
