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
import { BasicTable } from 'components/table/basic_table'
import type { Action } from 'models/action'
import type { Mapper } from 'models/mapper'
import React, { useEffect, useState, type ReactElement } from 'react'
import { useNavigate } from 'react-router-dom'
import mapperApi from 'services/api/mapper_api'
import NewMapperModal from './new_mapper_modal'

export default function DisplayMappers(): ReactElement {
  const [mappers, setMappers] = useState<Mapper[]>([])
  const [newMapperModalOpen, setNewMapperModalOpen] = React.useState(false)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const navigate = useNavigate()

  const getMappers = (): void => {
    mapperApi
      .getMappers()
      .then((mappers) => {
        setMappers(mappers)
        setIsLoading(false)
      })
      .catch((x) => {
        console.error('Failed to get mappers', x)
      })
  }

  useEffect(() => {
    getMappers()
    // const intervalId = setInterval(() => {
    //     getMappers()
    // }, 2000)
    // return () => clearInterval(intervalId)
  }, [])

  const handleNewMapperClick = (event: React.MouseEvent): void => {
    setNewMapperModalOpen(true)
  }
  const handleMappingAction = (mapperUid: string, action: Action): void => {
    navigate(`/mapping/${mapperUid}`)
  }

  return (
    <React.Fragment>
      <Button onClick={handleNewMapperClick}>New mapper</Button>
      <BasicTable
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
        data={mappers.map((mapper) => {
          return {
            uid: mapper.uid,
            name: mapper.name,
            attributeSchemaName: mapper.attributeSchemaName,
          }
        })}
        rowsSelectable={false}
        onRowAction={handleMappingAction}
        isLoading={isLoading}
      />
      <NewMapperModal open={newMapperModalOpen} setOpen={setNewMapperModalOpen} />
    </React.Fragment>
  )
}
