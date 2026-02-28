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

import {
  Button,
  Card,
  CardActions,
  CardContent,
  CardHeader,
  LinearProgress,
  TextField,
} from '@mui/material'
import Grid from '@mui/material/Grid'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import React from 'react'
import Spinner from 'src/components/spinner'
import { Batch } from 'src/models/batch'
import batchApi from 'src/services/api/batch.api'
import { queryKeys } from 'src/services/query_keys'

interface DisplayBatchProps {
  batchUid: string
  setOpen: React.Dispatch<React.SetStateAction<boolean>>
}

export default function DisplayBatch({
  batchUid,
  setOpen,
}: DisplayBatchProps): React.ReactElement {
  const [name, setName] = React.useState<string>()
  const queryClient = useQueryClient()
  const batchQuery = useQuery({
    queryKey: queryKeys.batch.detail(batchUid),
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
      queryClient.setQueryData(queryKeys.batch.detail(batch.uid), batch)
      queryClient.setQueryData(queryKeys.batch.details(), (old: Batch[]) => {
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
    <Spinner loading={batchQuery.isLoading}>
      <Card style={{ maxHeight: '80vh', overflowY: 'auto' }}>
        <CardHeader
          title={'Edit Batch: ' + (batchQuery.data.name ?? 'Unnamed Batch')}
        />
        <CardContent>
          <Grid size={{ xs: 12 }}>
            <TextField
              label="Batch Name"
              variant="standard"
              onChange={(event) => setName(event.target.value)}
              defaultValue={batchQuery.data.name}
              autoFocus
              slotProps={{
                inputLabel: {
                  shrink: true,
                },
              }}
            />
          </Grid>
        </CardContent>

        <CardActions disableSpacing>
          <Button onClick={handleUpdate}>Update</Button>
          <Button onClick={() => setOpen(false)}>Close</Button>
        </CardActions>
      </Card>
    </Spinner>
  )
}
