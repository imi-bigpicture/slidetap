import { ProjectStatus } from './status'
import { ItemSchema } from './schema'

export interface Project {
    uid: string
    name: string
    status: ProjectStatus
    itemSchemas: ItemSchema[]
    itemCounts: number[]
}
