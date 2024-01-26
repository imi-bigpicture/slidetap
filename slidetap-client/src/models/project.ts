import type { Attribute } from './attribute'
import type { ItemSchema, ProjectSchema } from './schema'
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
  attributes: Record<string, Attribute<any, any>>
  schema: ProjectSchema
}

export interface ProjectValidation {
  is_valid: boolean
}