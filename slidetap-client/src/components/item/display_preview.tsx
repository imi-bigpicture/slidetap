import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import { Accordion, AccordionDetails, AccordionSummary, TextField } from '@mui/material'
import type { ItemPreview } from 'models/item'
import React, { useEffect, useState } from 'react'
import itemApi from 'services/api/item_api'

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
  const [preview, setPreview] = useState<ItemPreview>()
  useEffect(() => {
    if (!showPreview) {
      return
    }
    const getPreview = (itemUid: string): void => {
      itemApi
        .getPreview(itemUid)
        .then((responsePreview) => {
          setPreview(responsePreview)
        })
        .catch((x) => {
          console.error('Failed to get preview', x)
        })
    }
    getPreview(itemUid)
  }, [itemUid, showPreview])
  return (
    <Accordion
      expanded={showPreview}
      onChange={(event, expanded) => {
        setShowPreview(expanded)
      }}
    >
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>Preview</AccordionSummary>
      <AccordionDetails>
        <TextField multiline fullWidth value={preview?.preview} />
      </AccordionDetails>
    </Accordion>
  )
}
