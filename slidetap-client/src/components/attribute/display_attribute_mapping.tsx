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

import { Stack, TextField } from '@mui/material'
import type { Attribute } from 'models/attribute'
import type { Mapper, MappingItem } from 'models/mapper'
import React, { useEffect, useState } from 'react'
import mapperApi from 'services/api/mapper_api'

interface DisplayAttributeMappingProps {
  attribute: Attribute<any, any>
}

export default function DisplayAttributeMapping({
  attribute,
}: DisplayAttributeMappingProps): React.ReactElement {
  const [mapping, setMapping] = useState<MappingItem>()
  const [mapper, setMapper] = useState<Mapper>()
  useEffect(() => {
    const getMapping = (mappingItemUid: string): void => {
      mapperApi
        .getMapping(mappingItemUid)
        .then((mappingItem) => {
          setMapping(mappingItem)
        })
        .catch((x) => {
          console.error('Failed to get mapping', x)
        })
    }
    if (attribute.mappingItemUid === undefined) {
      return
    }
    getMapping(attribute.mappingItemUid)
  }, [attribute.mappingItemUid])
  useEffect(() => {
    const getMapper = (mapperUid: string): void => {
      mapperApi
        .get(mapperUid)
        .then((mapper) => {
          setMapper(mapper)
        })
        .catch((x) => {
          console.error('Failed to get mapper', x)
        })
    }
    if (mapping === undefined) {
      return
    }
    getMapper(mapping.mapperUid)
  }, [mapping])
  return (
    <Stack spacing={1} direction="row" sx={{ margin: 1 }}>
      <TextField
        size="small"
        label="Mappable value"
        value={attribute.mappableValue ?? ''}
        InputProps={{ readOnly: true }}
      />
      <TextField
        size="small"
        label="Mapper"
        value={mapper?.name ?? ''}
        InputProps={{ readOnly: true }}
      />
      <TextField
        size="small"
        label="Expression"
        value={mapping?.expression ?? ''}
        InputProps={{ readOnly: true }}
      />
    </Stack>
  )
}
