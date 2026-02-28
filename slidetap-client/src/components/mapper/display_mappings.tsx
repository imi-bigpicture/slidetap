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
import Grid from '@mui/material/Grid'
import { useQuery } from '@tanstack/react-query'
import React, { type ReactElement } from 'react'
import { BasicTable } from 'src/components/table/basic_table'
import { Action } from 'src/models/action'
import type { Mapper, MappingItem } from 'src/models/mapper'
import mapperApi from 'src/services/api/mapper_api'
import { queryKeys } from 'src/services/query_keys'
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
    queryKey: queryKeys.mapper.mappings(mapper.uid),
    queryFn: async () => {
      return await mapperApi.getMappings(mapper.uid)
    },
  })

  const handleNewMappingClick = (): void => {
    setEditMappingOpen(true)
  }
  const handleMappingAction = (mapping: MappingItem): void => {
    setMappingUid(mapping.uid)
    setEditMappingOpen(true)
  }
  return (
    <Grid container spacing={1}>
      <Grid size={{ xs: 12 }}>
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
          actions={[{ action: Action.VIEW, onAction: handleMappingAction }]}
          topBarActions={[
            <Button key="new" onClick={handleNewMappingClick}>
              New mapping
            </Button>,
          ]}
          isLoading={mappingsQuery.isLoading}
        />
      </Grid>
      {editMappingOpen && (
        <Grid size={{ xs: 3 }}>
          <MappingDetails mappingUid={mappingUid} setOpen={setEditMappingOpen} />
        </Grid>
      )}
    </Grid>
  )
}
