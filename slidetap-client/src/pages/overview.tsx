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
import { useMemo, type ReactElement } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import OverviewView from 'src/components/overview/overview_view'
import { useSchemaContext } from 'src/contexts/schema/schema_context'
import type { TableRequest } from 'src/models/table_item'

export default function OverviewPage(): ReactElement {
  const { projectUid, itemUid, overviewLayoutUid } = useParams()
  const [searchParams] = useSearchParams()
  const rootSchema = useSchemaContext()

  if (!projectUid || !itemUid || !overviewLayoutUid) {
    throw new Error('Project, Item, and Overview Layout UIDs are required')
  }

  const overviewLayout = rootSchema.overviewLayouts.find(
    (layout) => layout.uid === overviewLayoutUid,
  )

  const tableRequest = useMemo<TableRequest | undefined>(() => {
    const raw = searchParams.get('tableRequest')
    if (!raw) return undefined
    try {
      return JSON.parse(raw) as TableRequest
    } catch {
      return undefined
    }
  }, [searchParams])

  const batchUid = searchParams.get('batchUid') ?? undefined

  if (!overviewLayout) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography>Overview layout not found</Typography>
      </Box>
    )
  }

  return (
    <Box sx={{ p: 2 }}>
      <OverviewView
        projectUid={projectUid}
        itemUid={itemUid}
        overviewLayout={overviewLayout}
        batchUid={batchUid}
        tableRequest={tableRequest}
      />
    </Box>
  )
}
