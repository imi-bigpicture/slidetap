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

import { Typography } from '@mui/material'
import { type ReactElement } from 'react'
import type { Mapper } from 'src/models/mapper'

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
