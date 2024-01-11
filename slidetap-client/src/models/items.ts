import type { Attribute } from './attribute'
import type { AnnotationSchema, ImageSchema, ObservationSchema, SampleSchema } from './schema'
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
  selected: boolean
  itemValueType: number
  attributes: Record<string, Attribute<any, any>>
  projectUid: string
}

export interface Sample extends Item {
  schema: SampleSchema
  parents: ItemReference[]
  children: ItemReference[]
  images: ItemReference[]
  observations: ItemReference[]
}

export interface Image extends Item {
  schema: ImageSchema
  status: ImageStatus
  samples: ItemReference[]
  annotations: ItemReference[]
  observations: ItemReference[]
}

export interface Observation extends Item {
  schema: ObservationSchema
  item: ItemReference
}

export interface Annotation extends Item {
  schema: AnnotationSchema
  image: ItemReference
  observations: ItemReference[]
}
