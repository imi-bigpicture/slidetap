import React, { type ReactElement } from 'react'
import { Typography } from '@mui/material'
import type { Mapper } from 'models/mapper'

interface MapperOverviewProps {
  mapper: Mapper
}
export default function MapperOverview({ mapper }: MapperOverviewProps): ReactElement {
  return (
    <>
      <Typography>Mapper overview</Typography>
      <Typography>Mapper name: {mapper.name}</Typography>
      <Typography>Attribute name: {mapper.attributeSchemaName}</Typography>
    </>
  )
}
