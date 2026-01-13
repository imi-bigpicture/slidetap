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

import { Button } from '@mui/material'
import Grid from '@mui/material/Grid'
import { useQuery } from '@tanstack/react-query'
import React, { type ReactElement } from 'react'
import { useNavigate } from 'react-router-dom'
import StatusChip from 'src/components/status_chip'
import { Action } from 'src/models/action'
import { Batch } from 'src/models/batch'
import {
  BatchStatus,
  BatchStatusList,
  BatchStatusStrings,
} from 'src/models/batch_status'
import type { Project } from 'src/models/project'
import batchApi from 'src/services/api/batch.api'
import { queryKeys } from 'src/services/query_keys'
import { BasicTable } from '../../table/basic_table'
import DisplayBatch from './display_batch'

interface ListBatchesProps {
  project: Project
  setBatchUid: (batchUid: string) => void
}

export default function ListBatches({
  project,
  setBatchUid,
}: ListBatchesProps): ReactElement {
  const [batchDetailsOpen, setBatchDetailsOpen] = React.useState(false)
  const [batchDetailsUid, setBatchDetailsUid] = React.useState<string>()
  const navigate = useNavigate()
  const batchQuery = useQuery({
    queryKey: queryKeys.batch.list(project.uid),
    queryFn: async () => {
      return await batchApi.getBatches(project.uid)
    },
  })

  const handleBatchEdit = (batch: Batch): void => {
    setBatchDetailsOpen(true)
    setBatchDetailsUid(batch.uid)
  }
  const handleBatchSelect = (batch: Batch): void => {
    setBatchUid(batch.uid)
  }
  const handleBatchDelete = (batch: Batch): void => {
    if (batch.isDefault) {
      return
    }
    batchApi
      .delete(batch.uid)
      .then(() => {
        const nextBBatch = batchQuery.data?.find((x) => x.uid !== batch.uid)
        if (nextBBatch === undefined) {
          throw new Error('Failed to find next batch')
        }
        batchQuery.refetch().then(() => setBatchUid(nextBBatch.uid))
      })
      .catch((x) => {
        console.error('Failed to delete batch', x)
      })
  }
  const handleCreateBatch = (): void => {
    batchApi
      .create('New batch', project.uid)
      .then((batch) => {
        setBatchUid(batch.uid)
        navigate(`/project/${project.uid}/batch/${batch.uid}`)
      })
      .catch((x) => {
        console.error('Failed to create batch', x)
      })
  }
  const handleBatchDeleteEnabled = (batch: Batch): boolean => {
    return !batch.isDefault
  }

  return (
    <Grid container spacing={1} justifyContent="flex-start" alignItems="flex-start">
      <Grid size={{ xs: batchDetailsOpen ? 8 : 12 }}>
        <BasicTable<Batch>
          columns={[
            {
              header: 'Name',
              accessorKey: 'name',
            },
            {
              header: 'Created',
              accessorKey: 'created',
              Cell: ({ row }) => new Date(row.original.created).toLocaleString('en-gb'),
              filterVariant: 'date-range',
            },
            {
              header: 'Status',
              accessorKey: 'status',
              Cell: ({ row }) => (
                <StatusChip
                  status={row.original.status}
                  stringMap={BatchStatusStrings}
                  colorMap={{
                    [BatchStatus.INITIALIZED]: 'secondary',
                    [BatchStatus.METADATA_SEARCHING]: 'primary',
                    [BatchStatus.METADATA_SEARCH_COMPLETE]: 'primary',
                    [BatchStatus.IMAGE_PRE_PROCESSING]: 'primary',
                    [BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE]: 'primary',
                    [BatchStatus.IMAGE_POST_PROCESSING]: 'primary',
                    [BatchStatus.IMAGE_POST_PROCESSING_COMPLETE]: 'success',
                    [BatchStatus.COMPLETED]: 'success',
                    [BatchStatus.FAILED]: 'error',
                    [BatchStatus.DELETED]: 'secondary',
                  }}
                  onClick={() => handleBatchSelect(row.original)}
                />
              ),
              filterVariant: 'multi-select',
              filterSelectOptions: BatchStatusList.map((status) => ({
                label: BatchStatusStrings[status],
                value: status.toString(),
              })),
            },
            {
              header: 'Default',
              accessorKey: 'isDefault',
              Cell: ({ row }) => (row.original.isDefault ? 'Yes' : 'No'),
            },
          ]}
          data={batchQuery.data ?? []}
          rowsSelectable={false}
          isLoading={batchQuery.isLoading}
          actions={[
            { action: Action.VIEW, onAction: handleBatchSelect },
            { action: Action.EDIT, onAction: handleBatchEdit },
            {
              action: Action.DELETE,
              onAction: handleBatchDelete,
              enabled: handleBatchDeleteEnabled,
            },
          ]}
          topBarActions={[
            <Button key="new" onClick={handleCreateBatch}>
              New batch
            </Button>,
          ]}
        />
      </Grid>
      {batchDetailsOpen && batchDetailsUid != null && (
        <Grid size={{ xs: 4 }}>
          <DisplayBatch batchUid={batchDetailsUid} setOpen={setBatchDetailsOpen} />
        </Grid>
      )}
    </Grid>
  )
}
