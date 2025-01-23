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

import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  LinearProgress,
  TextField,
} from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import React from 'react'
import itemApi from 'src/services/api/item_api'

interface DisplayPreviewProps {
  showPreview: boolean
  setShowPreview: React.Dispatch<React.SetStateAction<boolean>>
  itemUid: string
}

export default function DisplayPreview({
  showPreview,
  setShowPreview,
  itemUid,
}: DisplayPreviewProps): React.ReactElement {
  const previewQuery = useQuery({
    queryKey: ['preview', itemUid],
    queryFn: async () => {
      return await itemApi.getPreview(itemUid)
    },
    enabled: showPreview,
  })
  if (!showPreview) {
    return <></>
  }
  if (previewQuery.data === undefined) {
    return <LinearProgress />
  }
  return (
    <Accordion
      expanded={showPreview}
      onChange={(_, expanded) => {
        setShowPreview(expanded)
      }}
    >
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>Preview</AccordionSummary>
      <AccordionDetails>
        <TextField multiline fullWidth value={previewQuery.data} />
      </AccordionDetails>
    </Accordion>
  )
}
