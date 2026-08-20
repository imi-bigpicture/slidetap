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
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import React, { useState, type ReactElement } from 'react'
import { useNavigate } from 'react-router-dom'
import { BasicTable } from 'src/components/table/basic_table'
import { useError } from 'src/contexts/error/error_context'
import { Action } from 'src/models/action'
import { Mapper, MapperGroup } from 'src/models/mapper'
import mapperApi from 'src/services/api/mapper_api'
import schemaApi from 'src/services/api/schema_api'
import { queryKeys } from 'src/services/query_keys'
import MapperGroupMappersModal from './mapper_group_mappers_modal'
import NewMapperGroupModal from './new_mapper_group_modal'
import NewMapperModal from './new_mapper_modal'

export default function ListMappers(): ReactElement {
  const [newMapperModalOpen, setNewMapperModalOpen] = React.useState(false)
  const [newGroupModalOpen, setNewGroupModalOpen] = React.useState(false)
  const [mapperToEdit, setMapperToEdit] = React.useState<Mapper>()
  const [groupToEdit, setGroupToEdit] = React.useState<MapperGroup>()

  const [tabValue, setTabValue] = useState(0)

  const navigate = useNavigate()
  const { showError } = useError()
  const queryClient = useQueryClient()
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
  const attributeSchemasQuery = useQuery({
    queryKey: queryKeys.schema.attributes(),
    queryFn: async () => {
      return await schemaApi.getAttributeSchemas()
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (mapper: Mapper) => {
      return await mapperApi.delete(mapper.uid)
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.mapper.all })
    },
    onError: (error) => {
      showError('Failed to delete mapper', error)
    },
  })

  const navigteToMapping = (mapper: Mapper): void => {
    navigate(`/mapping/${mapper.uid}`)
  }
  const handleEdit = (mapper: Mapper): void => {
    setMapperToEdit(mapper)
    setNewMapperModalOpen(true)
  }
  const handleDelete = (mapper: Mapper): void => {
    // ponytail: native confirm, swap for a dialog if the design calls for one.
    if (!window.confirm(`Delete mapper "${mapper.name}" and all its mappings?`)) {
      return
    }
    deleteMutation.mutate(mapper)
  }
  const attributeSchemaName = (attributeSchemaUid: string): string =>
    attributeSchemasQuery.data?.find((schema) => schema.uid === attributeSchemaUid)
      ?.displayName ?? ''
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
                id: 'attributeSchemaName',
                accessorFn: (mapper) => attributeSchemaName(mapper.attributeSchemaUid),
              },
            ]}
            data={mappersQuery.data ?? []}
            rowsSelectable={false}
            actions={[
              { action: Action.VIEW, onAction: navigteToMapping },
              { action: Action.EDIT, onAction: handleEdit },
              { action: Action.DELETE, onAction: handleDelete },
            ]}
            isLoading={mappersQuery.isLoading}
            topBarActions={[
              <Button
                key="new"
                onClick={() => {
                  setMapperToEdit(undefined)
                  setNewMapperModalOpen(true)
                }}
              >
                New mapper
              </Button>,
            ]}
          />
        </TabPanel>
        <TabPanel value={1}>
          <BasicTable<MapperGroup>
            columns={[
              {
                header: 'Name',
                accessorKey: 'name',
              },
              {
                header: 'Mappers',
                id: 'mappers',
                accessorFn: (group) =>
                  group.mappers
                    .map(
                      (mapperUid) =>
                        mappersQuery.data?.find((mapper) => mapper.uid === mapperUid)
                          ?.name,
                    )
                    .filter((name) => name !== undefined)
                    .join(', '),
              },
            ]}
            data={mappgerGroupsQuery.data ?? []}
            rowsSelectable={false}
            actions={[{ action: Action.EDIT, onAction: setGroupToEdit }]}
            isLoading={mappgerGroupsQuery.isLoading}
            topBarActions={[
              <Button key="new" onClick={() => setNewGroupModalOpen(true)}>
                New group
              </Button>,
            ]}
          />
        </TabPanel>
      </TabContext>

      <NewMapperModal
        open={newMapperModalOpen}
        setOpen={setNewMapperModalOpen}
        mapper={mapperToEdit}
      />
      <NewMapperGroupModal open={newGroupModalOpen} setOpen={setNewGroupModalOpen} />
      {groupToEdit !== undefined && (
        <MapperGroupMappersModal
          open={true}
          setOpen={() => setGroupToEdit(undefined)}
          group={groupToEdit}
        />
      )}
    </React.Fragment>
  )
}
