import type { ProjectStatus } from './status'
import type { ItemSchema } from './schema'

export interface Project {
  uid: string
  name: string
  status: ProjectStatus
  itemSchemas: ItemSchema[]
  itemCounts: number[]
}
