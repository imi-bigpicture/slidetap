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
import Grid from '@mui/material/Unstable_Grid2/Grid2'
import { BasicTable } from 'components/table/basic_table'
import type { Action } from 'models/action'
import type { Mapper, MappingItem } from 'models/mapper'
import React, { useEffect, useState, type ReactElement } from 'react'
import mapperApi from 'services/api/mapper_api'
import MappingDetails from './mapping_details'

interface DisplayMappingsProps {
  mapper: Mapper
}

export default function DisplayMappings({
  mapper,
}: DisplayMappingsProps): ReactElement {
  const [mappings, setMappings] = useState<MappingItem[]>([])
  const [editMappingOpen, setEditMappingOpen] = React.useState(false)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [mappingUid, setMappingUid] = React.useState<string>()

  useEffect(() => {
    const getMappings = (): void => {
      mapperApi
        .getMappings(mapper.uid)
        .then((response) => {
          setMappings(response)
          setIsLoading(false)
        })
        .catch((x) => {
          console.error('Failed to get items', x)
        })
    }
    getMappings()
  }, [mapper.uid])
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
          data={mappings.map((mapping) => {
            return {
              uid: mapping.uid,
              expression: mapping.expression,
              displayValue: mapping.attribute.displayValue,
            }
          })}
          rowsSelectable={false}
          onRowAction={handleMappingAction}
          isLoading={isLoading}
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
