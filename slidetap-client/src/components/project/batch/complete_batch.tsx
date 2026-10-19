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
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ReactElement } from 'react'
import { Batch } from 'src/models/batch'
import { BatchStatus } from 'src/models/batch_status'
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
  // Said before completing is tried rather than only as the refusal: what is
  // left to verify is work to go and do, not a fault.
  const verificationQuery = useQuery({
    queryKey: queryKeys.batch.verification(batch.uid),
    queryFn: async () => await batchApi.getVerification(batch.uid),
  })
  const completeBatchMutation = useMutation({
    mutationFn: async (batchUid: string) => await batchApi.complete(batchUid),
    // Its error is shown beside the action.
    meta: { handlesError: true },
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
  // The server refuses it as well; this only saves trying what the warning
  // already says will be refused.
  const blockedByVerification = (verificationQuery.data?.blocking.length ?? 0) > 0
  // Read from the batch as it was last fetched, which locking updates.
  const shownBatch = completeBatchMutation.data ?? batch
  const locked = [
    BatchStatus.LOCKED,
    BatchStatus.IMAGE_STORING,
    BatchStatus.COMPLETED,
  ].includes(shownBatch.status)
  const handleCompleteBatch = (): void => {
    completeBatchMutation.mutate(batch.uid)
  }

  return (
    <Grid size={{ xs: 4 }}>
      <Stack spacing={1}>
        <Typography variant="body2" color="text.secondary">
          Locking the batch closes what it holds to editing once it is curated.
          Everything in it has to be valid, or taken out of the project, and where the
          project verifies batches, the units drawn have to be verified. A locked batch
          can be reopened from the batch list until its images are stored to the outbox,
          which is done for the whole project from its Export page.
        </Typography>
        {locked && (
          <Alert severity="success">
            The batch is locked. Store its images to the outbox from the project's
            Export page once every batch is locked.
          </Alert>
        )}
        {!locked && blockedByVerification && (
          <Alert severity="warning">
            Verifying holds the batch back:
            {verificationQuery.data?.blocking.map((reason) => (
              <div key={reason}>{reason}</div>
            ))}
          </Alert>
        )}
        {!locked && (
          <Button
            disabled={completeBatchMutation.isPending || blockedByVerification}
            onClick={handleCompleteBatch}
          >
            Lock
          </Button>
        )}
        {completeBatchMutation.isError && (
          <Alert severity="error">{refusal(completeBatchMutation.error)}</Alert>
        )}
      </Stack>
    </Grid>
  )
}
