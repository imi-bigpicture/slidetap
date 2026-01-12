import { Button, Stack } from '@mui/material'
import Grid from '@mui/material/Grid'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import React, { ReactElement } from 'react'
import { Batch } from 'src/models/batch'
import batchApi from 'src/services/api/batch.api'

interface CompleteBatchesProps {
  batch: Batch
}

export default function CompleteBatches({ batch }: CompleteBatchesProps): ReactElement {
  const queryClient = useQueryClient()
  const [completing, setCompleting] = React.useState(false)
  const completeBatchMutation = useMutation({
    mutationFn: (batchUid: string) => {
      return batchApi.complete(batchUid)
    },
    onSuccess: (updatedBatch) => {
      queryClient.setQueryData(['batch', batch.uid], updatedBatch)
    },
  })
  const handleCompleteBatch = (): void => {
    setCompleting(true)
    completeBatchMutation.mutate(batch.uid)
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
