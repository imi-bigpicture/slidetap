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

import CssBaseline from '@mui/material/CssBaseline'
import { LocalizationProvider } from '@mui/x-date-pickers'
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { type ReactElement } from 'react'
import { useEffect, type ReactElement } from 'react'
import { Route, BrowserRouter as Router, Routes } from 'react-router-dom'
import ProtectedRoute from 'src/components/auth/protected_route'
import SessionTimeoutDialog from 'src/components/auth/session_timeout_dialog'
import ErrorBoundary from 'src/components/error/error_boundary'
import Login from 'src/components/login/basic_login'
import { ErrorProvider } from 'src/contexts/error/error_context'
import { SchemaContextProvider } from 'src/contexts/schema/schema_context_provider'
import ImagesForItemPage from 'src/pages/images_for_item'
import ItemPage from 'src/pages/item'
import MappingPage from 'src/pages/mapper'
import MappersPage from 'src/pages/mappers'
import ProjectPage from 'src/pages/project'
import ProjectsPage from 'src/pages/projects'
import SchemasPage from 'src/pages/schemas'
import Title from 'src/pages/title'
import auth from 'src/services/auth'
const queryClient = new QueryClient()

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30000,
    },
  },
})

function App(): ReactElement {
  // Initialize cross-tab synchronization
  useEffect(() => {
    auth.initCrossTabSync()
  }, [])

  return (
    <QueryClientProvider client={queryClient}>
      <LocalizationProvider dateAdapter={AdapterDateFns}>
        <Router>
          {!auth.isLoggedIn() ? (
            <Login />
          ) : (
            <SchemaContextProvider>
              <CssBaseline enableColorScheme />
      <ErrorProvider>
        <ErrorBoundary>
          <LocalizationProvider dateAdapter={AdapterDateFns}>
            <CssBaseline enableColorScheme />
            <Router>
              <Routes>
                <Route path="/" element={<Title />} />
                <Route path="/mapping" element={<MappersPage />} />
                <Route path="/mapping/:mappingUid/*" element={<MappingPage />} />
                <Route path="/project" element={<ProjectsPage />} />
                <Route path="/project/:projectUid/*" element={<ProjectPage />} />
                <Route path="/schemas" element={<SchemasPage />} />
                <Route path="/login" element={<Login />} />
                <Route
                  path="/"
                  element={
                    <ProtectedRoute>
                      <SchemaContextProvider>
                        <Title />
                      </SchemaContextProvider>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/mapping"
                  element={
                    <ProtectedRoute>
                      <SchemaContextProvider>
                        <MappersPage />
                      </SchemaContextProvider>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/mapping/:mappingUid/*"
                  element={
                    <ProtectedRoute>
                      <SchemaContextProvider>
                        <MappingPage />
                      </SchemaContextProvider>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/project"
                  element={
                    <ProtectedRoute>
                      <SchemaContextProvider>
                        <ProjectsPage />
                      </SchemaContextProvider>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/project/:projectUid/*"
                  element={
                    <ProtectedRoute>
                      <SchemaContextProvider>
                        <ProjectPage />
                      </SchemaContextProvider>
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/schemas"
                  element={
                    <ProtectedRoute>
                      <SchemaContextProvider>
                        <SchemasPage />
                      </SchemaContextProvider>
                    </ProtectedRoute>
                  }
                />
                <Route
                  key="images_for_item"
                  path="/project/:projectUid/images_for_item/:itemUid"
                  element={
                    <ProtectedRoute>
                      <SchemaContextProvider>
                        <ImagesForItemPage />
                      </SchemaContextProvider>
                    </ProtectedRoute>
                  }
                />
                <Route
                  key="item"
                  path="/project/:projectUid/item/:itemUid"
                  element={
                    <ProtectedRoute>
                      <SchemaContextProvider>
                        <ItemPage />
                      </SchemaContextProvider>
                    </ProtectedRoute>
                  }
                />
              </Routes>
            </Router>
          </LocalizationProvider>
        </ErrorBoundary>
      </ErrorProvider>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}

export default App
