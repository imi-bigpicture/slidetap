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
import { Settings } from '@mui/icons-material'
import { LinearProgress } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import React, { useState } from 'react'
import { Route, useNavigate } from 'react-router-dom'
import MapperOverview from 'src/components/mapper/mapper_overview'
import Unmapped from 'src/components/mapper/unmapped_mapper'
import SideBar, { type MenuSection } from 'src/components/side_bar'
import mapperApi from 'src/services/api/mapper_api'
import DisplayMappingAttributes from './display_mapping_attributes'
import DisplayMappings from './display_mappings'

interface DisplayMapperProps {
  mapperUid: string
}

export default function DisplayMapper({
  mapperUid,
}: DisplayMapperProps): React.ReactElement {
  const [view, setView] = useState<string>('')
  const navigate = useNavigate()

  function changeView(view: string): void {
    setView(view)
    navigate(view)
  }
  const mapperQuery = useQuery({
    queryKey: ['mapper', mapperUid],
    queryFn: async () => {
      if (mapperUid === undefined) {
        return undefined
      }
      return await mapperApi.get(mapperUid)
    },
    enabled: mapperUid !== undefined,
  })
  if (mapperQuery.data === undefined) {
    return <LinearProgress />
  }

  const mainSection: MenuSection = {
    title: 'Mapper',
    name: mapperQuery.data.name,
    items: [
      {
        name: 'Settings',
        path: 'settings',
        icon: <Settings />,
        description: 'Mapper settings',
      },
      {
        name: 'Mappings',
        path: 'mappings',
        icon: <Settings />,
      },
      {
        name: 'Attributes',
        path: 'attributes',
        icon: <Settings />,
        description: 'Mapper attributes',
      },
      {
        name: 'Unmapped',
        path: 'unmapped',
        icon: <Settings />,
        description: 'Unmapped items in the mapper',
      },
    ],
  }
  const sections = [mainSection]

  const routes = [
    <Route
      key="overview"
      path="/"
      element={<MapperOverview mapper={mapperQuery.data} />}
    />,
    <Route
      key="mappings"
      path="/mappings"
      element={<DisplayMappings mapper={mapperQuery.data} />}
    />,
    <Route
      key="attributes"
      path="/attributes"
      element={<DisplayMappingAttributes mapper={mapperQuery.data} />}
    />,
    // (<Route key="test" path="/test" element={<TestMapper mapper={mapper} />} />),
    <Route
      key="unmapped"
      path="/unmapped"
      element={<Unmapped mapper={mapperQuery.data} />}
    />,
  ]
  return (
    <SideBar
      sections={sections}
      routes={routes}
      selectedView={view}
      changeView={changeView}
    />
  )
}
