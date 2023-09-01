import { Attribute } from 'models/attribute'
import { Mapping } from 'models/mapper'
import { AttributeSchema } from 'models/schema'

import { get, post } from 'services/api/api_methods'

const projectApi = {

    getAttribute: async (
        attributeUid: string
    ) => {
        return await get(`attribute/${attributeUid}`)
            .then<Attribute<any>>(async response => await response.json())
    },

    updateAttribute: async (
        attribute: Attribute<any>
    ) => {
        return await post(`attribute/${attribute.uid}/update`, attribute)
    },

    createAttribute: async (
        attribute: Attribute<any>
    ) => {
        return await post(`create/${attribute.schemaUid}/create`, attribute)
            .then<Attribute<any>>(async response => await response.json())
    },

    getMapping: async (
        attributeUid: string
    ) => {
        return await get(`attribute/${attributeUid}/mapping`)
            .then<Mapping>(async response => await response.json())
    },

    getSchemas: async (
        schemaUid: string
    ) => {
        return await get(`attribute/schemas/${schemaUid}`)
            .then<AttributeSchema[]>(async response => await response.json())
    },

    getAttributesForSchema: async (
        attributeSchemaUid: string
    ) => {
        return await get(`attribute/schema/${attributeSchemaUid}`)
            .then<Array<Attribute<any>>>(async response => await response.json())
    }

}

export default projectApi
