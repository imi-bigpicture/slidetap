import { Button, Stack } from '@mui/material'
import Grid from '@mui/material/Grid2'
import { useQueryClient } from '@tanstack/react-query'
import React, { ReactElement } from 'react'
import { Batch } from 'src/models/batch'
import batchApi from 'src/services/api/batch.api'

interface CompleteBatchesProps {
  batch: Batch
}

export default function CompleteBatches({ batch }: CompleteBatchesProps): ReactElement {
  const queryClient = useQueryClient()
  const [completing, setCompleting] = React.useState(false)
  const handleCompleteBatch = (): void => {
    setCompleting(true)
    batchApi
      .complete(batch.uid)
      .then((updatedBatch) => {
        queryClient.setQueryData(['batch', batch.uid], updatedBatch)
      })
      .catch((x) => {
        console.error('Failed to download project', x)
      })
  }

  return (
    <Grid size={{ xs: 4 }}>
      <Stack spacing={1}>
        <Button disabled={completing} onClick={handleCompleteBatch}>
          Complete
        </Button>
      </Stack>
    </Grid>
  )
}
