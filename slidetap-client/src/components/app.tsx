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
import { MutationCache, QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { useEffect, useState, type ReactElement, type ReactNode } from 'react'
import { Outlet, Route, BrowserRouter as Router, Routes } from 'react-router-dom'
import ProtectedRoute from 'src/components/auth/protected_route'
import SessionTimeoutDialog from 'src/components/auth/session_timeout_dialog'
import ErrorBoundary from 'src/components/error/error_boundary'
import Login from 'src/components/login/basic_login'
import { useError } from 'src/contexts/error/error_context'
import { ErrorProvider } from 'src/contexts/error/error_context_provider'
import { SchemaContextProvider } from 'src/contexts/schema/schema_context_provider'
import { PseudonymProvider } from 'src/contexts/pseudonym/pseudonym_provider'
import { ThemeContextProvider } from 'src/contexts/theme/theme_context_provider'
import { ExtensionsContext, type AppExtensions } from 'src/extensions'
import { useIsLoggedIn } from 'src/hooks/use_is_logged_in'
import { usePeriodicKeepAlive } from 'src/hooks/use_periodic_keepalive'
import MappingPage from 'src/pages/mapper'
import MappersPage from 'src/pages/mappers'
import ProjectPage from 'src/pages/project'
import ProjectsPage from 'src/pages/projects'
import SchemasPage from 'src/pages/schemas'
import TasksPage from 'src/pages/tasks'
import Title from 'src/pages/title'
import { AuthenticationError } from 'src/services/api/api_methods'
import auth from 'src/services/auth'

/** Layout component that wraps all protected routes with schema context */
function ProtectedLayout(): ReactElement {
  return (
    <ProtectedRoute>
      <SchemaContextProvider>
        <Outlet />
      </SchemaContextProvider>
    </ProtectedRoute>
  )
}

function createQueryClient(
  showError: (message: string, error?: unknown) => void,
): QueryClient {
  return new QueryClient({
    // A mutation that fails is shown to the user, unless it handles the error
    // itself: by an `onError` of its own, or by `meta: { handlesError: true }`
    // where it catches what `mutateAsync` throws. A request turned away as
    // unauthenticated is not reported, as it leads to the login page.
    mutationCache: new MutationCache({
      onError: (error, _variables, _context, mutation) => {
        if (
          mutation.options.onError !== undefined ||
          mutation.meta?.handlesError === true ||
          error instanceof AuthenticationError
        ) {
          return
        }
        const message = error instanceof Error ? error.message : 'Request failed'
        showError(message, error)
      },
    }),
    defaultOptions: {
      queries: {
        // A request turned away as unauthenticated is not tried again: it ends
        // the session, and the login page is shown instead.
        retry: (failureCount, error) =>
          !(error instanceof AuthenticationError) && failureCount < 1,
        refetchOnWindowFocus: false,
        staleTime: 30000,
      },
    },
  })
}

/** Provides the query client, reporting failed mutations in the error display
 * it is placed under. */
function QueryProvider({ children }: { children: ReactNode }): ReactElement {
  const { showError } = useError()
  // Made once. The `showError` it is made with only sets the error display's
  // state, so it keeps reporting for as long as the display is up.
  const [queryClient] = useState(() => createQueryClient(showError))

  const isLoggedIn = useIsLoggedIn()
  // What was fetched for one user is not shown to the next one logging in.
  useEffect(() => {
    if (!isLoggedIn) {
      queryClient.clear()
    }
  }, [isLoggedIn, queryClient])

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}

interface AppProps {
  extensions?: AppExtensions
}

function App({ extensions = {} }: AppProps): ReactElement {
  // Initialize cross-tab synchronization
  useEffect(() => {
    auth.initCrossTabSync()
  }, [])

  // Enable periodic keep-alive to maintain session for active users
  usePeriodicKeepAlive()

  const isLoggedIn = useIsLoggedIn()

  return (
    <ExtensionsContext.Provider value={extensions}>
      <ErrorProvider>
        <QueryProvider>
          <LocalizationProvider dateAdapter={AdapterDateFns}>
            <ThemeContextProvider>
              <PseudonymProvider>
                <CssBaseline enableColorScheme />
                <Router>
                  <ErrorBoundary>
                    <Routes>
                      <Route path="/login" element={<Login />} />
                      <Route element={<ProtectedLayout />}>
                        <Route path="/" element={<Title />} />
                        <Route path="/mapping" element={<MappersPage />} />
                        <Route path="/mapping/:mapperUid/*" element={<MappingPage />} />
                        <Route path="/project" element={<ProjectsPage />} />
                        <Route
                          path="/project/:projectUid/*"
                          element={<ProjectPage />}
                        />
                        {/* The views of an item are routed inside the project,
                            so that following one keeps the project's own bar
                            beside it rather than replacing the application with
                            a bare page. */}
                        <Route path="/schemas" element={<SchemasPage />} />
                        <Route path="/tasks" element={<TasksPage />} />
                      </Route>
                    </Routes>
                    {isLoggedIn && <SessionTimeoutDialog />}
                  </ErrorBoundary>
                </Router>
              </PseudonymProvider>
            </ThemeContextProvider>
          </LocalizationProvider>
        </QueryProvider>
      </ErrorProvider>
    </ExtensionsContext.Provider>
  )
}

export default App
