import { BatchStatus } from "./batch_status"

export interface Batch {
    readonly uid: string
    readonly name: string
    readonly status: BatchStatus
    readonly projectUid: string
    readonly isDefault: boolean
    readonly created: string
}