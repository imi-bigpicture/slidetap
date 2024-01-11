import type { Attribute } from './attribute'
import type { ItemSchema } from './schema'
import type { ImageStatus } from './status'

export interface ItemReference {
  uid: string
  name: string
  schemaDisplayName: string
  schemaUid: string
}

export interface Item {
  uid: string
  name: string
  schema: ItemSchema
  selected: boolean
  itemValueType: number
  attributes: Record<string, Attribute<any, any>>
  projectUid: string
}

export interface Sample extends Item {
  parents: ItemReference[]
  children: ItemReference[]
}

export interface Image extends Item {
  status: ImageStatus
  samples: ItemReference[]
}

export interface Observation extends Item {
  item: ItemReference
}
