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
import { Box } from '@mui/system'
import { LocalizationProvider } from '@mui/x-date-pickers'
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFnsV3'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { type ReactElement } from 'react'
import { Route, BrowserRouter as Router, Routes } from 'react-router-dom'
import Header from 'src/components/header'
import Login from 'src/components/login/basic_login'
import DisplayMapper from 'src/components/mapper/display_mapper'
import DisplayMappers from 'src/components/mapper/display_mappers'
import DisplayProject from 'src/components/project/display_project'
import ListProjects from 'src/components/project/list_projects'
import DisplaySchemas from 'src/components/schema/display_schemas'
import Title from 'src/components/title'
import { SchemaContextProvider } from 'src/contexts/schema/schema_context_provider'
import auth from 'src/services/auth'
import ImagesForItem from './image/images_for_item'

const queryClient = new QueryClient()

function App(): ReactElement {
  return (
    <QueryClientProvider client={queryClient}>
      <LocalizationProvider dateAdapter={AdapterDateFns} adapterLocale={'en-gb'}>
        <Router>
          <Header />
          <Box margin={0}>
            {!auth.isLoggedIn() ? (
              <Login />
            ) : (
              <SchemaContextProvider>
                <CssBaseline enableColorScheme />

                <Routes>
                  <Route path="/" element={<Title />} />
                  <Route path="/mapping" element={<DisplayMappers />} />
                  <Route path="/mapping/:mappingUid/*" element={<DisplayMapper />} />
                  <Route path="/project" element={<ListProjects />} />
                  <Route path="/project/:projectUid/*" element={<DisplayProject />} />
                  <Route
                    key="images_for_item"
                    path="/project/:projectUid/images_for_item/:itemUid"
                    element={<ImagesForItem />}
                  />
                  <Route path="/schemas" element={<DisplaySchemas />} />
                </Routes>
              </SchemaContextProvider>
            )}
          </Box>
        </Router>
      </LocalizationProvider>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}

export default App
