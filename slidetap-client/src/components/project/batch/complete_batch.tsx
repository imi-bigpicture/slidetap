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

import { Button, Stack } from '@mui/material'
import Grid from '@mui/material/Grid'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import React, { ReactElement } from 'react'
import { Batch } from 'src/models/batch'
import batchApi from 'src/services/api/batch.api'
import { queryKeys } from 'src/services/query_keys'

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
      queryClient.setQueryData(queryKeys.batch.detail(batch.uid), updatedBatch)
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
