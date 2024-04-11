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

import { Table, TableBody, TableCell, TableHead, TableRow } from '@mui/material'
import React, { useEffect, type ReactElement } from 'react'
import type { Mapper } from 'models/mapper'
import mapperApi from 'services/api/mapper_api'

interface UnmappedProps {
  mapper: Mapper
}

export default function Unmapped({ mapper }: UnmappedProps): ReactElement {
  const [values, setValues] = React.useState<string[]>([])

  useEffect(() => {
    const getMappers = (): void => {
      mapperApi
        .getUnmappedValues(mapper.uid)
        .then((values) => {
          setValues(values)
        })
        .catch((x) => {console.error('Failed to get unmapepd values', x)})
    }
    getMappers()
    const intervalId = setInterval(() => {
      getMappers()
    }, 2000)
    return () => {clearInterval(intervalId)}
  }, [mapper.uid])

  return (
    <Table>
      <TableHead>
        <TableRow>
          <TableCell>Value</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {values.map((value) => (
          <TableRow key={value}>
            <TableCell>{value}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
