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

import { Box, LinearProgress, Tab, Tabs, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import React, { useState } from 'react'
import itemApi from 'src/services/api/item_api'
import { queryKeys } from 'src/services/query_keys'

interface ExportPreviewProps {
  itemUid: string
}

/** What the metadata export writes for an item and everything connected to
 * it, such as a case with its samples, images and observations, one tab per
 * file it is written to. */
export default function ExportPreview({
  itemUid,
}: ExportPreviewProps): React.ReactElement {
  const [fileIndex, setFileIndex] = useState(0)
  const previewQuery = useQuery({
    queryKey: queryKeys.item.exportPreview(itemUid),
    queryFn: async () => await itemApi.getExportPreview(itemUid),
  })
  if (previewQuery.isLoading) {
    return <LinearProgress />
  }
  if (previewQuery.isError) {
    return (
      <Typography color="error" sx={{ p: 2 }}>
        The export could not be previewed: {previewQuery.error.message}
      </Typography>
    )
  }
  const files = previewQuery.data?.files ?? []
  if (files.length === 0) {
    return <Typography sx={{ p: 2 }}>Nothing is exported for this.</Typography>
  }
  const shownIndex = Math.min(fileIndex, files.length - 1)
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      <Tabs
        value={shownIndex}
        onChange={(_, value: number) => setFileIndex(value)}
        variant="scrollable"
        sx={{ minHeight: 32, '& .MuiTab-root': { minHeight: 32, py: 0 } }}
      >
        {files.map((file) => (
          <Tab key={file.name} label={file.name} sx={{ textTransform: 'none' }} />
        ))}
      </Tabs>
      <Box
        component="pre"
        sx={{
          m: 0,
          p: 1,
          overflow: 'auto',
          fontFamily: 'monospace',
          fontSize: '0.8rem',
          // The export indents with tabs, which would otherwise be 8 wide.
          tabSize: 2,
          bgcolor: 'action.hover',
          borderRadius: 1,
        }}
      >
        {files[shownIndex].content}
      </Box>
    </Box>
  )
}
