export enum ItemType {
    SAMPLE = 1,
    IMAGE = 2,
    ANNOTATION = 3,
    OBSERVATION = 4
}

export interface AttributeSchema {
    uid: string
    tag: string
    schemaDisplayName: string
}

export interface ItemSchema {
    uid: string
    name: string
    itemValueType: ItemType
    attributes: AttributeSchema[]
}
