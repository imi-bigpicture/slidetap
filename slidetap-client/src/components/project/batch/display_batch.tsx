import { Button, LinearProgress, TextField } from '@mui/material'
import Grid from '@mui/material/Grid2'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import React from 'react'
import { useParams } from 'react-router-dom'
import { Batch } from 'src/models/batch'
import batchApi from 'src/services/api/batch.api'

export default function DisplayBatch(): React.ReactElement {
  const [name, setName] = React.useState<string>()
  const { batchUid } = useParams()
  const queryClient = useQueryClient()
  const batchQuery = useQuery({
    queryKey: ['batch', batchUid],
    queryFn: async () => {
      if (batchUid === undefined) {
        return undefined
      }
      return await batchApi.get(batchUid)
    },
  })
  const mutateBatch = useMutation({
    mutationFn: async (batch: Batch) => {
      return await batchApi.update(batch)
    },
    onSuccess: (batch) => {
      queryClient.setQueryData(['batch', batch.uid], batch)
      queryClient.setQueryData(['batches'], (old: Batch[]) => {
        return old.map((b) => {
          if (b.uid === batch.uid) {
            return batch
          }
          return b
        })
      })
    },
  })

  const handleUpdate = () => {
    if (batchQuery.data === undefined || name === undefined) {
      return
    }
    const newBatch = { ...batchQuery.data, name: name }
    mutateBatch.mutate(newBatch)
  }

  if (batchQuery.isLoading || batchQuery.data === undefined) {
    return <LinearProgress />
  }
  return (
    <Grid container spacing={1} justifyContent="flex-start" alignItems="flex-start">
      {/* <Grid size={{ xs: 12 }}>
        <StepHeader title="Batch settings" />
      </Grid> */}
      <Grid size={{ xs: 2 }}>
        <TextField
          label="Batch Name"
          variant="standard"
          onChange={(event) => setName(event.target.value)}
          defaultValue={batchQuery.data.name}
          autoFocus
        />
      </Grid>
      <Grid size={{ xs: 12 }}>
        <Button onClick={handleUpdate}>Update</Button>
      </Grid>
    </Grid>
  )
}
