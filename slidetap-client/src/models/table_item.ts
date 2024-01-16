import type { Attribute } from './attribute'
import type { ItemReference } from './item'
import type { ImageStatus, ProjectStatus, ValueStatus } from './status'



export interface TableAttribute {
  uid: string
  diplayValue: string
  mappingStatus: ValueStatus
}

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

export interface ItemTableItem extends TableItem {
  name: string
  selected: boolean
  attributes: Record<string, Attribute<any, any>>
}

export interface SampleTableItem extends ItemTableItem {
  name: string
  parents: ItemReference[]
  children: ItemReference[]
}

export interface ImageTableItem extends ItemTableItem {
  name: string
  status: ImageStatus
  samples: ItemReference[]
}

export interface AnnotationTableItem extends ItemTableItem {
  name: string
  image: ItemReference
}

export interface ObservationTableItem extends ItemTableItem {
  name: string
  item: ItemReference
}

export enum Action {
  NEW = 1,
  VIEW = 2,
  EDIT = 3,
  DELETE = 4,
  RESTORE = 5,
  COPY = 6,
}

export const ActionStrings = {
  [Action.NEW]: 'New',
  [Action.VIEW]: 'View',
  [Action.EDIT]: 'Edit',
  [Action.DELETE]: 'Delete',
  [Action.RESTORE]: 'Restore',
  [Action.COPY]: 'Copy',
}

