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

import { Box, Typography } from '@mui/material'
import { type ReactElement } from 'react'
import { useParams } from 'react-router-dom'
import OverviewView from 'src/components/overview/overview_view'
import { useSchemaContext } from 'src/contexts/schema/schema_context'

export default function OverviewPage(): ReactElement {
  const { itemUid, overviewLayoutUid } = useParams()
  const rootSchema = useSchemaContext()

  if (!itemUid || !overviewLayoutUid) {
    throw new Error('Item UID and Overview Layout UID are required')
  }

  const overviewLayout = rootSchema.overviewLayouts.find(
    (layout) => layout.uid === overviewLayoutUid,
  )

  if (!overviewLayout) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography>Overview layout not found</Typography>
      </Box>
    )
  }

  return (
    <Box sx={{ p: 2 }}>
      <OverviewView itemUid={itemUid} overviewLayout={overviewLayout} />
    </Box>
  )
}
