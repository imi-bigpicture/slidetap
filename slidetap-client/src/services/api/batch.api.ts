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

import type { Batch } from 'src/models/batch'
import type { BatchStatus } from 'src/models/batch_status'
import { BatchValidation } from 'src/models/validation'

import { delete_, get, post, postFile } from 'src/services/api/api_methods'

const batchApi = {
  create: async (name: string, projectUid: string) => {
    return await post('/batches/create', { name, projectUid }).then<Batch>(
      async (response) => await response.json(),
    )
  },

  update: async (batch: Batch) => {
    return await post(`batches/batch/${batch.uid}`, batch).then<Batch>(
      async (response) => await response.json())
  },

  get: async (batchUid: string) => {
    return await get(`batches/batch/${batchUid}`).then<Batch>(
      async (response) => await response.json(),
    )
  },

  getBatches: async (projectUid?: string, status?: BatchStatus) => {
      const params = new URLSearchParams();
      if (projectUid !== undefined) {
        params.append('project_uid', projectUid)
      }

    if (status !== undefined) {
      params.append('status', status.toString())
    }
    const url = "batches" + (params.size > 0 ? "?" + params.toString() : "")
    return await get(url).then<Batch[]>(
      async (response) => await response.json(),
    )
  },

  delete: async (batchUid: string) => {
    return await delete_(`batches/batch/${batchUid}`)
  },

  uploadBatchFile: async (batchUid: string, file: File) => {
    return await postFile(`batches/batch/${batchUid}/uploadFile`, file).then<Batch>(
      async (response) => await response.json())
  },

  preProcess: async (batchUid: string) => {
    return await post(`batches/batch/${batchUid}/pre_process`).then<Batch>(
      async (response) => await response.json())
  },

  process: async (batchUid: string) => {
    return await post(`batches/batch/${batchUid}/process`).then<Batch>(
      async (response) => await response.json())
  },
  getValidation: async (batchUid: string) => {
    return await get(`batches/batch/${batchUid}/validation`).then<BatchValidation>(
      async (response) => await response.json(),
    )
  },
  complete: async (batchUid: string) => {
    return await post(`batches/batch/${batchUid}/complete`).then<Batch>(
      async (response) => await response.json(),
    )
  }
}

export default batchApi
