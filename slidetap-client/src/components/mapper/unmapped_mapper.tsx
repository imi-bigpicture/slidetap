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

import {
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
} from '@mui/material'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import React from 'react'
import type { Mapper } from 'src/models/mapper'
import mapperApi from 'src/services/api/mapper_api'
import { queryKeys } from 'src/services/query_keys'

interface UnmappedProps {
  mapper: Mapper
}

export default function Unmapped({ mapper }: UnmappedProps): React.ReactElement {
  // const [values, setValues] = React.useState<string[]>([])
  const valuesQuery = useQuery({
    queryKey: queryKeys.mapper.unmappedAttributes(mapper.uid),
    queryFn: async () => {
      return await mapperApi.getUnmappedValues(mapper.uid)
    },
    placeholderData: keepPreviousData,
  })

  if (valuesQuery.data === undefined) {
    return <LinearProgress />
  }
  return (
    <Table>
      <TableHead>
        <TableRow>
          <TableCell>Value</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {valuesQuery.data.map((value) => (
          <TableRow key={value}>
            <TableCell>{value}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
