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

import { BatchStatus } from "./batch_status"

export interface BatchCreate {
    readonly name: string
    readonly projectUid: string
}

export interface Batch {
    readonly uid: string
    readonly name: string
    readonly status: BatchStatus
    /** When the status last changed, null if unknown. */
    readonly statusUpdated: string | null
    readonly statusMessage: string | null
    readonly projectUid: string
    readonly isDefault: boolean
    readonly created: string
    /** Folder of the batch's own bundle, null if stored with its project. */
    readonly storageFolder: string | null
}

/** Whether the batch is stored and exported on its own, not with its project. */
export function storedAlone(batch: Batch): boolean {
    return batch.storageFolder !== null && batch.storageFolder !== undefined
}

/** How far storing the images of a batch to the outbox has come, counted over
 * the selected images the batch stores. */
export interface BatchStoringProgress {
    readonly batchUid: string
    /** How many images the batch stores. */
    readonly total: number
    /** How many of them are in the outbox. */
    readonly stored: number
    /** How many failed to store, and wait to be retried or taken out. */
    readonly failed: number
}