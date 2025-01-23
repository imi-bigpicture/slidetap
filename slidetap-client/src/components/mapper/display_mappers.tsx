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

import { Button } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import React, { type ReactElement } from 'react'
import { useNavigate } from 'react-router-dom'
import { BasicTable } from 'src/components/table/basic_table'
import { Action } from 'src/models/action'
import { Mapper } from 'src/models/mapper'
import mapperApi from 'src/services/api/mapper_api'
import NewMapperModal from './new_mapper_modal'

export default function DisplayMappers(): ReactElement {
  const [newMapperModalOpen, setNewMapperModalOpen] = React.useState(false)
  const navigate = useNavigate()
  const mappersQuery = useQuery({
    queryKey: ['mappers'],
    queryFn: async () => {
      return await mapperApi.getMappers()
    },
  })

  const handleNewMapperClick = (): void => {
    setNewMapperModalOpen(true)
  }
  const navigteToMapping = (mapper: Mapper): void => {
    navigate(`/mapping/${mapper.uid}`)
  }

  return (
    <React.Fragment>
      <Button onClick={handleNewMapperClick}>New mapper</Button>
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
        actions={[[Action.VIEW, navigteToMapping]]}
        isLoading={mappersQuery.isLoading}
      />
      <NewMapperModal open={newMapperModalOpen} setOpen={setNewMapperModalOpen} />
    </React.Fragment>
  )
}
