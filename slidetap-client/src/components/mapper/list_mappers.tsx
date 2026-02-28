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

import { TabContext, TabList, TabPanel } from '@mui/lab'
import { Button, Tab } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import React, { useState, type ReactElement } from 'react'
import { useNavigate } from 'react-router-dom'
import { BasicTable } from 'src/components/table/basic_table'
import { Action } from 'src/models/action'
import { Mapper } from 'src/models/mapper'
import mapperApi from 'src/services/api/mapper_api'
import { queryKeys } from 'src/services/query_keys'
import NewMapperGroupModal from './new_mapper_group_modal'
import NewMapperModal from './new_mapper_modal'

export default function ListMappers(): ReactElement {
  const [newMapperModalOpen, setNewMapperModalOpen] = React.useState(false)
  const [newGroupModalOpen, setNewGroupModalOpen] = React.useState(false)

  const [tabValue, setTabValue] = useState(0)

  const navigate = useNavigate()
  const mappersQuery = useQuery({
    queryKey: queryKeys.mapper.all,
    queryFn: async () => {
      return await mapperApi.getMappers()
    },
  })
  const mappgerGroupsQuery = useQuery({
    queryKey: queryKeys.mapperGroup.all,
    queryFn: async () => {
      return await mapperApi.getMapperGroups()
    },
  })

  const navigteToMapping = (mapper: Mapper): void => {
    navigate(`/mapping/${mapper.uid}`)
  }
  return (
    <React.Fragment>
      <TabContext value={tabValue}>
        <TabList onChange={(_, newValue) => setTabValue(newValue)}>
          <Tab label="Mappers" />
          <Tab label="Groups" />
        </TabList>
        <TabPanel value={0}>
          <BasicTable<Mapper>
            columns={[
              {
                header: 'Name',
                accessorKey: 'name',
              },
              {
                header: 'Attribute',
                accessorKey: 'attributeSchemaName',
              },
            ]}
            data={mappersQuery.data ?? []}
            rowsSelectable={false}
            actions={[{ action: Action.VIEW, onAction: navigteToMapping }]}
            isLoading={mappersQuery.isLoading}
            topBarActions={[
              <Button key="new" onClick={() => setNewMapperModalOpen(true)}>
                New mapper
              </Button>,
            ]}
          />
        </TabPanel>
        <TabPanel value={1}>
          <BasicTable
            columns={[
              {
                header: 'Name',
                accessorKey: 'name',
              },
            ]}
            data={mappgerGroupsQuery.data ?? []}
            rowsSelectable={false}
            isLoading={mappgerGroupsQuery.isLoading}
            topBarActions={[
              <Button key="new" onClick={() => setNewGroupModalOpen(true)}>
                New group
              </Button>,
            ]}
          />
        </TabPanel>
      </TabContext>

      <NewMapperModal open={newMapperModalOpen} setOpen={setNewMapperModalOpen} />
      <NewMapperGroupModal open={newGroupModalOpen} setOpen={setNewGroupModalOpen} />
    </React.Fragment>
  )
}
