import type { ItemSchema } from './schema'
import type { ProjectStatus } from './status'

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

export interface ProjectValidation {
  is_valid: boolean
}