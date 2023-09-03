import { Mapper, MappingItem } from 'models/mapper'
import { Attribute } from 'models/attribute'
import { post, get } from 'services/api/api_methods'

const mapperApi = {

    create: async (
        name: string,
        attributeSchemaUid: string
    ) => {
        return await post('mapper/create', {
            name,
            attributeSchemaUid
        }).then<Mapper>(async response => await response.json())
    },

    save: async (
        mapperUid: string,
        mapping: string,
        mappedValue: Attribute<any, any>
    ) => {
        const formData = new FormData()
        formData.append('mapping', mapping)
        formData.append('mappedValue', JSON.stringify(mappedValue))

        return await post('mapper/' + mapperUid + '/save', formData)
    },

    delete: async (
        mapperUid: string,
        mapping: string
    ) => {
        const formData = new FormData()
        formData.append('mapping', mapping)
        return await post('mapper/' + mapperUid + '/delete', formData)
    },

    getMappers: async () => {
        return await get('mapper')
            .then<Mapper[]>(async response => await response.json())
    },

    get: async (
        mapperUid: string
    ) => {
        return await get('mapper/' + mapperUid)
            .then<Mapper>(async response => await response.json())
    },

    getUnmappedValues: async (
        mapperUid: string
    ) => {
        return await get('mapper/' + mapperUid + '/unmapped')
            .then<string[]>(async response => await response.json())
    },

    getForTag: async (
        tag: string
    ) => {
        return await post('mapper/tag/' + tag)
            .then<Mapper[]>(async response => await response.json())
    },

    getMappings: async (
        mapperUid: string
    ) => {
        return await get('mapper/' + mapperUid + '/mapping')
            .then<MappingItem[]>(async response => await response.json())
    },

    getMapping: async (
        mapperUid: string,
        mappingUid: string
    ) => {
        return await get('mapper/' + mapperUid + '/mapping/' + mappingUid)
            .then<MappingItem>(async response => await response.json())
    },

    getMappingAttributes: async (
        mapperUid: string
    ) => {
        return await get('mapper/' + mapperUid + '/attributes')
            .then<Array<Attribute<any, any>>>(async response => await response.json())
    }
}

export default mapperApi
