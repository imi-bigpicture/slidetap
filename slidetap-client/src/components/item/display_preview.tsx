import { Card, CardContent, CardHeader, TextField } from '@mui/material'
import React, { useEffect, useState } from 'react'
import itemApi from 'services/api/item_api'

interface DisplayPreviewProps {
  itemUid: string
}

export default function DisplayPreview({
  itemUid,
}: DisplayPreviewProps): React.ReactElement {
  const [preview, setPreview] = useState<string>()
  useEffect(() => {
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
  }, [itemUid])
  return (
    <Card style={{ maxHeight: '60vh', overflowY: 'auto' }}>
      <CardHeader title="Preview" />
      <CardContent>
        <TextField multiline fullWidth value={preview} />
      </CardContent>
    </Card>
  )
}
