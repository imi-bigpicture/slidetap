import type { Attribute } from './attribute'
import type { ImageStatus, MappingStatus, ProjectStatus } from './status'

export interface ItemReference {
  uid: string
  schemaName: string
  name: string
}

export interface TableAttribute {
  uid: string
  diplayValue: string
  mappingStatus: MappingStatus
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
  observedOn: ItemReference
}

export enum TableItemAction {
  VIEW = 1,
  EDIT = 2,
  DELETE = 3,
  COPY = 4,
}

export const TableItemActionStrings = {
  [TableItemAction.VIEW]: 'View',
  [TableItemAction.EDIT]: 'Edit',
  [TableItemAction.DELETE]: 'Delete',
  [TableItemAction.COPY]: 'Copy',
}
