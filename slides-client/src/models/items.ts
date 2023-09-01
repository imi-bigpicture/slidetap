import { Attribute } from './attribute'
import { ImageStatus } from './status'

export interface ItemReference {
    uid: string
    typeName: string
    name: string
}

export interface Item {
    uid: string
    name: string
    selected: boolean
    itemType: number
    attributes: Record<string, Attribute<any>>
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
    observedOn: ItemReference
}
