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

import { delete_, get, parseJsonResponse, post, postFile } from 'src/services/api/api_methods'

const batchApi = {
  create: async (name: string, projectUid: string) => {
    const response = await post('/batches/create', { name, projectUid })
    return await parseJsonResponse<Batch>(response)
  },

  update: async (batch: Batch) => {
    const response = await post(`batches/batch/${batch.uid}`, batch)
    return await parseJsonResponse<Batch>(response)
  },

  get: async (batchUid: string) => {
    const response = await get(`batches/batch/${batchUid}`)
    return await parseJsonResponse<Batch>(response)
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
    const response = await get(url)
    return await parseJsonResponse<Batch[]>(response)
  },

  delete: async (batchUid: string) => {
    return await delete_(`batches/batch/${batchUid}`)
  },

  uploadBatchFile: async (batchUid: string, file: File) => {
    const response = await postFile(`batches/batch/${batchUid}/uploadFile`, file)
    return await parseJsonResponse<Batch>(response)
  },

  preProcess: async (batchUid: string) => {
    const response = await post(`batches/batch/${batchUid}/pre_process`)
    return await parseJsonResponse<Batch>(response)
  },

  process: async (batchUid: string) => {
    const response = await post(`batches/batch/${batchUid}/process`)
    return await parseJsonResponse<Batch>(response)
  },

  getValidation: async (batchUid: string) => {
    const response = await get(`batches/batch/${batchUid}/validation`)
    return await parseJsonResponse<BatchValidation>(response)
  },

  complete: async (batchUid: string) => {
    const response = await post(`batches/batch/${batchUid}/complete`)
    return await parseJsonResponse<Batch>(response)
  }
}

export default batchApi
