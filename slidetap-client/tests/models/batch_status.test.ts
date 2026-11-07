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

import { describe, expect, it } from 'vitest'
import { BatchStatus, batchIsReadyToProcess } from 'src/models/batch_status'

describe('batchIsReadyToProcess', () => {
  it('is ready once pre-processed where the root pre-processes', () => {
    expect(batchIsReadyToProcess(BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE, true)).toBe(
      true,
    )
  })

  it('is not ready after the metadata search where the root pre-processes', () => {
    expect(batchIsReadyToProcess(BatchStatus.METADATA_SEARCH_COMPLETE, true)).toBe(
      false,
    )
  })

  it('is ready after the metadata search where the root does not pre-process', () => {
    expect(batchIsReadyToProcess(BatchStatus.METADATA_SEARCH_COMPLETE, false)).toBe(
      true,
    )
  })

  it('is still ready once pre-processed where the root no longer pre-processes', () => {
    expect(
      batchIsReadyToProcess(BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE, false),
    ).toBe(true)
  })

  it('is ready while pre-processing where the root no longer pre-processes', () => {
    expect(batchIsReadyToProcess(BatchStatus.IMAGE_PRE_PROCESSING, false)).toBe(true)
    expect(batchIsReadyToProcess(BatchStatus.IMAGE_PRE_PROCESSING, true)).toBe(false)
  })

  it('is not ready while searching or converting', () => {
    for (const status of [
      BatchStatus.METADATA_SEARCHING,
      BatchStatus.IMAGE_POST_PROCESSING,
      BatchStatus.IMAGE_POST_PROCESSING_COMPLETE,
    ]) {
      expect(batchIsReadyToProcess(status, false)).toBe(false)
      expect(batchIsReadyToProcess(status, true)).toBe(false)
    }
  })
})
