import type { Attribute } from './attribute'
import type { ItemReference } from './item'
import type { ImageStatus, ProjectStatus } from './status'


export interface TableItem {
  uid: string
}

export interface ProjectTableItem extends TableItem {
  name: string
  status: ProjectStatus
}

export interface MapperTableItem extends TableItem {
  name: string
  attribute: string
  targets: string[]
}

export interface Item extends TableItem {
  identifier: string
  name?: string
  pseudonym?: string
  selected: boolean
  valid: boolean
  attributes: Record<string, Attribute<any, any>>
}

export interface Sample extends Item {
  name: string
  parents: ItemReference[]
  children: ItemReference[]
}

export interface Image extends Item {
  name: string
  status: ImageStatus
  statusMessage: string
  samples: ItemReference[]
}

export interface Annotation extends Item {
  name: string
  image: ItemReference
}

export interface Observation extends Item {
  name: string
  item: ItemReference
}

export interface ColumnFilter  {
  id: string
  value: unknown
}

export interface TableRequest {
  start: number
  size: number
  identifierFilter?: string
  attributeFilters?: Record<string, string>
  included?: boolean
  valid?: boolean
}