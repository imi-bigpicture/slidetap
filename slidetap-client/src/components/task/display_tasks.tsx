//    Copyright 2026 SECTRA AB
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
  Alert,
  Box,
  FormControlLabel,
  MenuItem,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import React, { type ReactElement } from 'react'
import StatusChip from 'src/components/status_chip'
import { BasicDataTable } from 'src/components/table/basic_data_table'
import {
  TaskJob,
  TaskJobStatus,
  taskJobStatusLabels,
  taskJobStatuses,
} from 'src/models/task_job'
import taskApi from 'src/services/api/task_api'
import { queryKeys } from 'src/services/query_keys'

/** How often the list asks again.
 *
 * A queue is watched rather than read once, and a job that has just been
 * deferred is worth seeing without the reader reaching for the browser's
 * reload. Slow enough that a page left open is not a load of its own. */
const REFETCH_INTERVAL_MS = 5000

/** The task that keeps the queue honest rather than one the application asked
 * for.
 *
 * It runs on a schedule for as long as the worker is up, so it is most of what
 * the queue holds — 1740 of 1768 jobs in a development database — and showing
 * it by default would bury every import behind it. Hidden rather than dropped:
 * whether it is running, and whether it is failing, is exactly what somebody
 * looking at a stalled queue wants to know. */
const HOUSEKEEPING_TASK = 'slidetap:retry_stalled_jobs'

const statusColors: Record<
  TaskJobStatus,
  'success' | 'error' | 'primary' | 'secondary' | 'warning'
> = {
  todo: 'primary',
  doing: 'warning',
  succeeded: 'success',
  failed: 'error',
  cancelled: 'secondary',
  aborted: 'secondary',
}

/** A job as the table holds it: the row needs a string key, and the queue
 * numbers its jobs. */
interface TaskJobRow extends TaskJob {
  uid: string
}

/** The task name without the application prefix it is registered under.
 *
 * Every task in the queue carries the same prefix, so a column of them is a
 * column of one repeated word and the name that tells them apart is pushed
 * out of sight. The whole name is still what the filter matches on. */
function shortTaskName(taskName: string | null): string {
  if (taskName === null || taskName === undefined) return ''
  const separator = taskName.indexOf(':')
  return separator === -1 ? taskName : taskName.slice(separator + 1)
}

function formatScheduledAt(scheduledAt: string | null): string {
  if (scheduledAt === null || scheduledAt === undefined) return ''
  const parsed = new Date(scheduledAt)
  return Number.isNaN(parsed.getTime()) ? scheduledAt : parsed.toLocaleString()
}

/** The arguments the job was deferred with, on one line.
 *
 * What identifies the work is in here — which batch is being remapped, which
 * image is being fetched — so it earns a column, but only as much of it as a
 * row can hold. */
function formatArgs(args: Record<string, unknown> | null): string {
  if (args === null || args === undefined) return ''
  const entries = Object.entries(args)
  if (entries.length === 0) return ''
  return entries.map(([key, value]) => `${key}=${String(value)}`).join(', ')
}

export default function DisplayTasks(): ReactElement {
  const [status, setStatus] = React.useState<TaskJobStatus | ''>('')
  const [showHousekeeping, setShowHousekeeping] = React.useState(false)

  const filter = { status: status === '' ? undefined : status }
  const jobsQuery = useQuery({
    queryKey: queryKeys.task.jobs(filter),
    queryFn: async () => await taskApi.getJobs(filter),
    refetchInterval: REFETCH_INTERVAL_MS,
  })
  const countsQuery = useQuery({
    queryKey: queryKeys.task.counts(),
    queryFn: async () => await taskApi.getTaskCounts(),
    refetchInterval: REFETCH_INTERVAL_MS,
  })

  const jobs = jobsQuery.data ?? []
  const rows: TaskJobRow[] = jobs
    .filter((job) => showHousekeeping || job.taskName !== HOUSEKEEPING_TASK)
    .map((job) => ({ ...job, uid: job.id.toString() }))

  // Read off the per-task counts rather than off the rows: those are one
  // listing, cut to a limit and filtered, while this is what the queue holds.
  const totals = (countsQuery.data ?? []).reduce(
    (sum, task) => ({
      todo: sum.todo + task.todo,
      doing: sum.doing + task.doing,
      failed: sum.failed + task.failed,
    }),
    { todo: 0, doing: 0, failed: 0 },
  )

  return (
    <Stack spacing={2} sx={{ p: 2 }}>
      <Stack direction="row" spacing={2} sx={{ alignItems: 'center' }}>
        <Typography variant="h6">Background tasks</Typography>
        <Box sx={{ flexGrow: 1 }} />
        <Typography variant="body2" color="text.secondary">
          {totals.doing} running · {totals.todo} waiting · {totals.failed} failed
        </Typography>
      </Stack>
      {jobsQuery.isError && (
        <Alert severity="error">Could not read the task queue.</Alert>
      )}
      <Stack direction="row" spacing={2} sx={{ alignItems: 'center' }}>
        <TextField
          select
          size="small"
          label="Status"
          value={status}
          onChange={(event) => setStatus(event.target.value as TaskJobStatus | '')}
          sx={{ minWidth: 160 }}
        >
          {/* Not "all": the queue holds one row per piece of work it has ever
              done, and the successes among them are neither few nor read. How
              many there are is on the line above. */}
          <MenuItem value="">Unfinished and failed</MenuItem>
          {taskJobStatuses.map((candidate) => (
            <MenuItem key={candidate} value={candidate}>
              {taskJobStatusLabels[candidate]}
            </MenuItem>
          ))}
        </TextField>
        <FormControlLabel
          control={
            <Switch
              checked={showHousekeeping}
              onChange={(event) => setShowHousekeeping(event.target.checked)}
            />
          }
          label="Show stalled-job sweeps"
        />
      </Stack>
      <BasicDataTable<TaskJobRow>
        columns={[
          {
            id: 'taskName',
            header: 'Task',
            filter: { variant: 'text' },
            accessorFn: (job) => shortTaskName(job.taskName),
            grow: true,
          },
          {
            id: 'status',
            header: 'Status',
            filter: { variant: 'text' },
            accessorKey: 'status',
            Cell: ({ row }) => (
              <StatusChip<TaskJobStatus>
                status={row.status}
                colorMap={statusColors}
                stringMap={taskJobStatusLabels}
              />
            ),
          },
          {
            id: 'id',
            header: 'Job',
            accessorKey: 'id',
            size: 90,
          },
          {
            id: 'queue',
            header: 'Queue',
            filter: { variant: 'text' },
            accessorKey: 'queue',
          },
          {
            id: 'attempts',
            header: 'Attempts',
            accessorKey: 'attempts',
            size: 100,
          },
          {
            id: 'scheduledAt',
            header: 'Scheduled',
            accessorFn: (job) => formatScheduledAt(job.scheduledAt),
          },
          {
            id: 'args',
            header: 'Arguments',
            filter: { variant: 'text' },
            accessorFn: (job) => formatArgs(job.args),
            grow: true,
          },
        ]}
        data={rows}
        rowsSelectable={false}
        isLoading={jobsQuery.isLoading}
      />
    </Stack>
  )
}
