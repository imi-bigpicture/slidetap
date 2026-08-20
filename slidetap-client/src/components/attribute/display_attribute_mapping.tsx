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

import { Stack, TextField, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import React from 'react'
import type { Attribute, AttributeValueTypes } from 'src/models/attribute'
import mapperApi from 'src/services/api/mapper_api'
import { queryKeys } from 'src/services/query_keys'

interface DisplayAttributeMappingProps {
  attribute: Attribute<AttributeValueTypes>
}

/** The mapper and expression that matched the mappable value, if any. */
export default function DisplayAttributeMapping({
  attribute,
}: DisplayAttributeMappingProps): React.ReactElement {
  const mappingQuery = useQuery({
    queryKey: queryKeys.mapper.mapping(attribute.mappingItemUid ?? ''),
    queryFn: async () => {
      if (attribute.mappingItemUid === null) {
        return undefined
      }
      return await mapperApi.getMapping(attribute.mappingItemUid)
    },
    enabled: attribute.mappingItemUid !== null,
  })
  const mapperQuery = useQuery({
    queryKey: queryKeys.mapper.detail(
      mappingQuery.data !== undefined ? mappingQuery.data.mapperUid : '',
    ),
    queryFn: async () => {
      if (mappingQuery.data === undefined) {
        return undefined
      }
      return await mapperApi.get(mappingQuery.data.mapperUid)
    },
    enabled: mappingQuery.data !== undefined,
  })
  if (mappingQuery.data === undefined) {
    return (
      <Typography variant="caption" color="text.secondary">
        No mapping matched
      </Typography>
    )
  }
  return (
    <Stack spacing={1} direction="row">
      <TextField
        size="small"
        label="Mapper"
        fullWidth
        value={mapperQuery.data?.name ?? ''}
        slotProps={{
          input: { readOnly: true },
          inputLabel: { shrink: true },
        }}
      />
      <TextField
        size="small"
        label="Expression"
        fullWidth
        value={mappingQuery.data.expression}
        slotProps={{
          input: { readOnly: true },
          inputLabel: { shrink: true },
        }}
      />
    </Stack>
  )
}
