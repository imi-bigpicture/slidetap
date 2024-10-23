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

import React, { type ReactElement } from 'react'
import { createRoot } from 'react-dom/client'
import { Route, BrowserRouter as Router, Routes } from 'react-router-dom'
import DisplayProjects from './components/project/display_projects'
import './index.css'
// import Login from './components/oauth_login'
import Login from './components/login/basic_login'

import { Box } from '@mui/system'
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query'
import DisplayMapper from 'components/mapper/display_mapper'
import DisplayMappers from 'components/mapper/display_mappers'
import DisplaySchemas from 'components/schema/display_schemas'
import Title from 'components/title'
import Header from './components/header'
import DisplayProject from './components/project/display_project'
import auth from './services/auth'

const queryClient = new QueryClient()

function App(): ReactElement {
  useQuery({
    queryKey: 'keepAlive',
    queryFn: () => {
      auth.keepAlive()
    },
    refetchInterval: 30 * 1000,
  })
  return (
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
  )
}

const container = document.getElementById('root')
if (container !== null) {
  const root = createRoot(container)
  root.render(
    <React.StrictMode>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </React.StrictMode>,
  )
} else {
  console.error('Failed to create react root.')
}
