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
