import type { Attribute } from './attribute'
import type { AnnotationSchema, ImageSchema, ItemSchema, ObservationSchema, SampleSchema } from './schema'
import type { ImageStatus } from './status'

export interface ItemReference {
  uid: string
  identifier: string
  name?: string
  schemaDisplayName: string
  schemaUid: string
}

export interface ItemDetails {
  uid: string
  identifier: string
  name?: string
  pseodonym?: string
  selected: boolean
  itemValueType: number
  attributes: Record<string, Attribute<any, any>>
  projectUid: string
  schema: ItemSchema
  valid: boolean
}

export interface SampleDetails extends ItemDetails {
  schema: SampleSchema
  parents: ItemReference[]
  children: ItemReference[]
  images: ItemReference[]
  observations: ItemReference[]
}

export interface ImageDetails extends ItemDetails {
  schema: ImageSchema
  status: ImageStatus
  samples: ItemReference[]
  annotations: ItemReference[]
  observations: ItemReference[]
}

export interface ObservationDetails extends ItemDetails {
  schema: ObservationSchema
  item: ItemReference
}

export interface AnnotationDetails extends ItemDetails {
  schema: AnnotationSchema
  image: ItemReference
  observations: ItemReference[]
}

export interface ItemPreview {
  preview: string
}

export interface ItemValidation {
  is_valid: boolean
}