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
import { Route, BrowserRouter as Router, Routes } from 'react-router-dom'
import Login from 'src/components/login/basic_login'
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

function App(): ReactElement {
  return (
    <QueryClientProvider client={queryClient}>
      <LocalizationProvider dateAdapter={AdapterDateFns}>
        <Router>
          {!auth.isLoggedIn() ? (
            <Login />
          ) : (
            <SchemaContextProvider>
              <CssBaseline enableColorScheme />
              <Routes>
                <Route path="/" element={<Title />} />
                <Route path="/mapping" element={<MappersPage />} />
                <Route path="/mapping/:mappingUid/*" element={<MappingPage />} />
                <Route path="/project" element={<ProjectsPage />} />
                <Route path="/project/:projectUid/*" element={<ProjectPage />} />
                <Route path="/schemas" element={<SchemasPage />} />
                <Route
                  key="images_for_item"
                  path="/project/:projectUid/images_for_item/:itemUid"
                  element={<ImagesForItemPage />}
                />
                <Route
                  key="item"
                  path="/project/:projectUid/item/:itemUid"
                  element={<ItemPage />}
                />
              </Routes>
            </SchemaContextProvider>
          )}
        </Router>
      </LocalizationProvider>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}

export default App
