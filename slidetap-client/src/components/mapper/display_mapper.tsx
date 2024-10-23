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
import { LinearProgress } from '@mui/material'
import MapperOverview from 'components/mapper/mapper_overview'
import Unmapped from 'components/mapper/unmapped_mapper'
import SideBar, { type MenuSection } from 'components/side_bar'
import React, { useState } from 'react'
import { useQuery } from 'react-query'
import { Route, useNavigate } from 'react-router-dom'
import mapperApi from 'services/api/mapper_api'
import DisplayMappingAttributes from './display_mapping_attributes'
import DisplayMappings from './display_mappings'

const overviewSection = {
  name: 'Overview',
  path: '',
}

const mappingsSection = {
  name: 'Mappings',
  path: 'mappings',
}

const attributesSection = {
  name: 'Attributes',
  path: 'attributes',
}

const testSection: MenuSection = {
  name: 'Test',
  path: 'test',
}

const editSection: MenuSection = {
  name: 'Edit',
  path: 'edit',
}

const unmappedSection: MenuSection = {
  name: 'Unmapped',
  path: 'unmapped',
}

export default function DisplayMapper(): React.ReactElement {
  const [view, setView] = useState<string>('')
  const navigate = useNavigate()

  function changeView(view: string): void {
    setView(view)
    navigate(view)
  }
  const mappertUid = window.location.pathname.split('mapping/').pop()?.split('/')[0]
  const mapperQuery = useQuery({
    queryKey: ['mapper', mappertUid],
    queryFn: async () => {
      if (mappertUid === undefined) {
        return undefined
      }
      return await mapperApi.get(mappertUid)
    },
    enabled: mappertUid !== undefined,
  })
  if (mapperQuery.data === undefined) {
    return <LinearProgress />
  }

  const sections = [
    overviewSection,
    mappingsSection,
    attributesSection,
    testSection,
    editSection,
    unmappedSection,
  ]

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
