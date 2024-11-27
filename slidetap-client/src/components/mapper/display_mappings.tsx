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

import { Button, Grid } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { BasicTable } from 'components/table/basic_table'
import type { Action } from 'models/action'
import type { Mapper } from 'models/mapper'
import React, { type ReactElement } from 'react'
import mapperApi from 'services/api/mapper_api'
import MappingDetails from './mapping_details'

interface DisplayMappingsProps {
  mapper: Mapper
}

export default function DisplayMappings({
  mapper,
}: DisplayMappingsProps): ReactElement {
  const [editMappingOpen, setEditMappingOpen] = React.useState(false)
  const [mappingUid, setMappingUid] = React.useState<string>()
  const mappingsQuery = useQuery({
    queryKey: ['mappings', mapper.uid],
    queryFn: async () => {
      return await mapperApi.getMappings(mapper.uid)
    },
    select: (data) => {
      return data.map((mapping) => {
        return {
          uid: mapping.uid,
          expression: mapping.expression,
          displayValue: mapping.attribute.displayValue,
        }
      })
    },
  })

  const handleNewMappingClick = (event: React.MouseEvent): void => {
    setEditMappingOpen(true)
  }
  const handleMappingAction = (mappingUid: string, action: Action): void => {
    setMappingUid(mappingUid)
    setEditMappingOpen(true)
  }
  return (
    <Grid container spacing={2}>
      <Grid xs={12}>
        <Button onClick={handleNewMappingClick}>New mapping</Button>
      </Grid>
      <Grid xs>
        <BasicTable
          columns={[
            {
              header: 'Expression',
              accessorKey: 'expression',
            },
            {
              header: 'Value',
              accessorKey: 'displayValue',
            },
          ]}
          data={mappingsQuery.data ?? []}
          rowsSelectable={false}
          onRowAction={handleMappingAction}
          isLoading={mappingsQuery.isLoading}
        />
      </Grid>
      {editMappingOpen && (
        <Grid xs={3}>
          <MappingDetails mappingUid={mappingUid} setOpen={setEditMappingOpen} />
        </Grid>
      )}
    </Grid>
  )
}
