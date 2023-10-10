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
