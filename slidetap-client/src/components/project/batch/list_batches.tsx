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
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from '@mui/material'
import Grid from '@mui/material/Grid'
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import React, { type ReactElement } from 'react'
import StatusChip from 'src/components/status_chip'
import { useError } from 'src/contexts/error/error_context'
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
import { BasicDataTable } from '../../table/basic_data_table'
import DisplayBatch from './display_batch'

interface ListBatchesProps {
  project: Project
  setBatchUid: (batchUid: string) => void
}

/** What a batch can be for the user to delete it: nothing a worker holds,
 * nothing curated, and what a delete that did not finish left behind. A batch
 * still marked as deleting is among those: its delete may never have been
 * queued, and asking again is how it is queued. A queued one is not queued
 * twice. */
const DELETABLE_STATUSES = [
  BatchStatus.INITIALIZED,
  BatchStatus.METADATA_SEARCH_COMPLETE,
  BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE,
  BatchStatus.IMAGE_POST_PROCESSING_COMPLETE,
  BatchStatus.FAILED,
  BatchStatus.DELETING,
  BatchStatus.DELETED,
]

export default function ListBatches({
  project,
  setBatchUid,
}: ListBatchesProps): ReactElement {
  const [batchDetailsOpen, setBatchDetailsOpen] = React.useState(false)
  const [batchDetailsUid, setBatchDetailsUid] = React.useState<string>()
  const { showError } = useError()
  const queryClient = useQueryClient()
  const [pendingDelete, setPendingDelete] = React.useState<Batch | null>(null)
  const batchQuery = useQuery({
    queryKey: queryKeys.batch.list(project.uid),
    queryFn: async () => {
      return await batchApi.getBatches(project.uid)
    },
    // A batch being deleted is gone once the task that deletes it commits,
    // and asking again is what notices.
    refetchInterval: (query) =>
      (query.state.data ?? []).some((batch) => batch.status === BatchStatus.DELETING)
        ? 2000
        : false,
    placeholderData: keepPreviousData,
  })

  const handleBatchEdit = (batch: Batch): void => {
    setBatchDetailsOpen(true)
    setBatchDetailsUid(batch.uid)
  }
  const handleBatchSelect = (batch: Batch): void => {
    setBatchUid(batch.uid)
  }
  const deleteBatchMutation = useMutation({
    mutationFn: async (batchUid: string) => await batchApi.delete(batchUid),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.batch.all })
      // Taking a batch out of the project is also what can complete it.
      void queryClient.invalidateQueries({ queryKey: queryKeys.project.all })
    },
    onError: (error) => {
      showError('Failed to delete batch', error)
    },
    onSettled: () => {
      setPendingDelete(null)
    },
  })
  const confirmDeleteBatch = (): void => {
    if (pendingDelete === null) return
    deleteBatchMutation.mutate(pendingDelete.uid)
  }
  const handleBatchNotDeleting = (batch: Batch): boolean => {
    return batch.status !== BatchStatus.DELETING
  }
  const handleCreateBatch = (): void => {
    batchApi
      .create({ name: 'New batch', projectUid: project.uid })
      .then((batch) => {
        batchQuery.refetch().then(() => setBatchUid(batch.uid))
      })
      .catch((error) => {
        showError('Failed to create batch', error)
      })
  }
  const handleBatchDeleteEnabled = (batch: Batch): boolean => {
    return (
      !batch.isDefault &&
      DELETABLE_STATUSES.includes(batch.status) &&
      !deleteBatchMutation.isPending
    )
  }
  const reopenBatchMutation = useMutation({
    mutationFn: async (batchUid: string) => await batchApi.reopen(batchUid),
    onSuccess: (updatedBatch) => {
      queryClient.setQueryData(queryKeys.batch.detail(updatedBatch.uid), updatedBatch)
      void queryClient.invalidateQueries({ queryKey: queryKeys.batch.all })
      // Locking or unlocking a batch is also what decides whether the project
      // is completed, and the export it offers follows from that.
      void queryClient.invalidateQueries({ queryKey: queryKeys.project.all })
    },
    onError: (error) => {
      showError('Failed to reopen batch', error)
    },
  })
  const handleBatchReopen = (batch: Batch): void => {
    reopenBatchMutation.mutate(batch.uid)
  }
  const handleBatchReopenEnabled = (batch: Batch): boolean => {
    // Not while one is being reopened: what the row says is what was last read,
    // and it says locked until the answer arrives.
    return batch.status === BatchStatus.LOCKED && !reopenBatchMutation.isPending
  }

  return (
    <>
      <Grid
        container
        spacing={1}
        sx={{ justifyContent: 'flex-start', alignItems: 'flex-start' }}
      >
        <Grid size={{ xs: batchDetailsOpen ? 8 : 12 }}>
          <BasicDataTable<Batch>
            columns={[
              {
                id: 'name',
                filter: { variant: 'text' },
                header: 'Name',
                accessorKey: 'name',
              },
              {
                id: 'created',
                header: 'Created',
                accessorKey: 'created',
                Cell: ({ row }) => new Date(row.created).toLocaleString('en-gb'),
                filter: { variant: 'date-range' },
              },
              {
                id: 'status',
                header: 'Status',
                accessorKey: 'status',
                Cell: ({ row }) => (
                  <StatusChip
                    status={row.status}
                    stringMap={BatchStatusStrings}
                    colorMap={{
                      [BatchStatus.INITIALIZED]: 'secondary',
                      [BatchStatus.METADATA_SEARCHING]: 'primary',
                      [BatchStatus.METADATA_SEARCH_COMPLETE]: 'primary',
                      [BatchStatus.IMAGE_PRE_PROCESSING]: 'primary',
                      [BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE]: 'primary',
                      [BatchStatus.IMAGE_POST_PROCESSING]: 'primary',
                      [BatchStatus.IMAGE_POST_PROCESSING_COMPLETE]: 'success',
                      [BatchStatus.LOCKED]: 'success',
                      [BatchStatus.COMPLETED]: 'success',
                      [BatchStatus.IMAGE_STORING]: 'primary',
                      [BatchStatus.FAILED]: 'error',
                      [BatchStatus.DELETING]: 'warning',
                      [BatchStatus.DELETED]: 'secondary',
                    }}
                    onClick={() => handleBatchSelect(row)}
                  />
                ),
                filter: {
                  variant: 'multi-select',
                  options: BatchStatusList.map((status) => ({
                    label: BatchStatusStrings[status],
                    value: status.toString(),
                  })),
                },
              },
              {
                id: 'isDefault',
                filter: { variant: 'text' },
                header: 'Default',
                accessorKey: 'isDefault',
                Cell: ({ row }) => (row.isDefault ? 'Yes' : 'No'),
              },
            ]}
            data={batchQuery.data ?? []}
            rowsSelectable={false}
            isLoading={batchQuery.isLoading}
            actions={[
              {
                action: Action.VIEW,
                onAction: handleBatchSelect,
                enabled: handleBatchNotDeleting,
              },
              {
                action: Action.EDIT,
                onAction: handleBatchEdit,
                enabled: handleBatchNotDeleting,
              },
              {
                action: Action.REOPEN,
                onAction: handleBatchReopen,
                enabled: handleBatchReopenEnabled,
              },
              {
                action: Action.DELETE,
                onAction: setPendingDelete,
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
      <Dialog
        open={pendingDelete !== null}
        onClose={() => {
          if (!deleteBatchMutation.isPending) setPendingDelete(null)
        }}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>Delete batch?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete <strong>{pendingDelete?.name}</strong>? Its
            items and any image files it holds will be removed in the background. This
            action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setPendingDelete(null)}
            disabled={deleteBatchMutation.isPending}
          >
            Cancel
          </Button>
          <Button
            onClick={confirmDeleteBatch}
            color="error"
            variant="contained"
            disabled={deleteBatchMutation.isPending}
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </>
  )
}
