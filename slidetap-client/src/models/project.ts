import type { ProjectStatus } from './status'
import type { ItemSchema } from './schema'

export interface ProjectItem {
  count: number,
  schema: ItemSchema
}

export interface Project {
  uid: string
  name: string
  status: ProjectStatus
  items: ProjectItem[]
}
