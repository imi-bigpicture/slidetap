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

/** One job in the background queue, as the queue holds it. */
export interface TaskJob {
  id: number
  taskName: string
  queue: string
  status: TaskJobStatus
  priority: number
  attempts: number
  scheduledAt: string | null
  args: Record<string, unknown>
  lock: string | null
  workerId: number | null
  abortRequested: boolean
}

/** How many jobs of each status one task, or one queue, holds. */
export interface TaskCounts {
  name: string
  jobsCount: number
  todo: number
  doing: number
  succeeded: number
  failed: number
  cancelled: number
  aborted: number
}

/** The statuses Procrastinate gives a job. */
export type TaskJobStatus =
  | 'todo'
  | 'doing'
  | 'succeeded'
  | 'failed'
  | 'cancelled'
  | 'aborted'

export const taskJobStatuses: TaskJobStatus[] = [
  'todo',
  'doing',
  'succeeded',
  'failed',
  'cancelled',
  'aborted',
]

/** Read as the queue's own wording rather than translated: these are the words
 * in the Procrastinate documentation and in the worker's logs, and a page that
 * renamed them would not match what is read beside it. */
export const taskJobStatusLabels: Record<TaskJobStatus, string> = {
  todo: 'Todo',
  doing: 'Doing',
  succeeded: 'Succeeded',
  failed: 'Failed',
  cancelled: 'Cancelled',
  aborted: 'Aborted',
}
