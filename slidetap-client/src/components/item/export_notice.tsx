//    Copyright 2026 SECTRA AB
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

import { Alert, Stack } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import React from 'react'
import itemApi from 'src/services/api/item_api'
import { queryKeys } from 'src/services/query_keys'

interface ExportNoticesProps {
  itemUid: string
  /** Not asked for where the project is view only, which the server refuses
   * as it refuses the preview. */
  enabled?: boolean
}

/** How the item is exported, where that differs from how it is stored, such
 * as a case exported as one case per specimen: one alert for each way it does.
 * Nothing where it does not. */
export default function ExportNotices({
  itemUid,
  enabled = true,
}: ExportNoticesProps): React.ReactElement | null {
  const noticesQuery = useQuery({
    queryKey: queryKeys.item.exportNotices(itemUid),
    queryFn: async () => {
      return await itemApi.getExportNotices(itemUid)
    },
    enabled,
  })
  const notices = noticesQuery.data?.notices ?? []
  if (notices.length === 0) {
    return null
  }
  return (
    <Stack spacing={1}>
      {notices.map((notice) => (
        <Alert key={notice.kind} severity="info" variant="outlined">
          {notice.message}
        </Alert>
      ))}
    </Stack>
  )
}
