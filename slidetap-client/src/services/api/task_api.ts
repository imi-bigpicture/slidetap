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

import { TaskCounts, TaskJob, TaskJobStatus } from 'src/models/task_job'
import { get, parseJsonResponse } from 'src/services/api/api_methods'

export interface TaskJobFilter {
  status?: TaskJobStatus
  task?: string
  queue?: string
  limit?: number
}

const taskApi = {
  getJobs: async (filter?: TaskJobFilter) => {
    const args = new Map<string, string | null | undefined>([
      ['status', filter?.status],
      ['task', filter?.task],
      ['queue', filter?.queue],
      ['limit', filter?.limit?.toString()],
    ])
    const response = await get('tasks/jobs', args)
    return await parseJsonResponse<TaskJob[]>(response)
  },

  getTaskCounts: async () => {
    const response = await get('tasks/tasks')
    return await parseJsonResponse<TaskCounts[]>(response)
  },

  getQueueCounts: async () => {
    const response = await get('tasks/queues')
    return await parseJsonResponse<TaskCounts[]>(response)
  },
}

export default taskApi
