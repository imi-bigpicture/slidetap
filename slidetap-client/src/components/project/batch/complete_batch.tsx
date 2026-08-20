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

import { Alert, Button, Stack, Typography } from '@mui/material'
import Grid from '@mui/material/Grid'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ReactElement } from 'react'
import { Batch } from 'src/models/batch'
import { ApiError } from 'src/services/api/api_methods'
import batchApi from 'src/services/api/batch.api'
import { queryKeys } from 'src/services/query_keys'

interface CompleteBatchesProps {
  batch: Batch
}

/** What the server said it would not do, rather than that something failed. */
function refusal(error: Error | null): string | undefined {
  if (error === null) {
    return undefined
  }
  return error instanceof ApiError ? (error.body ?? error.message) : error.message
}

export default function CompleteBatches({ batch }: CompleteBatchesProps): ReactElement {
  const queryClient = useQueryClient()
  const completeBatchMutation = useMutation({
    mutationFn: async (batchUid: string) => await batchApi.complete(batchUid),
    onSuccess: (updatedBatch) => {
      queryClient.setQueryData(queryKeys.batch.detail(batch.uid), updatedBatch)
      // The lists of batches say what each one is, and one of them just
      // changed: the batch list offers reopening on that, and refuses it on
      // what it last read.
      void queryClient.invalidateQueries({ queryKey: queryKeys.batch.all })
      // Locking or unlocking a batch is also what decides whether the project
      // is completed, and the export it offers follows from that.
      void queryClient.invalidateQueries({ queryKey: queryKeys.project.all })
    },
  })
  const handleCompleteBatch = (): void => {
    completeBatchMutation.mutate(batch.uid)
  }

  return (
    <Grid size={{ xs: 4 }}>
      <Stack spacing={1}>
        <Typography variant="body2" color="text.secondary">
          Completing the batch locks what it holds. Everything in it has to be valid, or
          taken out of the project. Reopening it again is done from the batch list.
        </Typography>
        <Button disabled={completeBatchMutation.isPending} onClick={handleCompleteBatch}>
          Complete
        </Button>
        {completeBatchMutation.isError && (
          <Alert severity="error">{refusal(completeBatchMutation.error)}</Alert>
        )}
      </Stack>
    </Grid>
  )
}
