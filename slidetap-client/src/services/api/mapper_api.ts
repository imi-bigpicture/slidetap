import type { Mapper, MappingItem } from 'models/mapper'
import type { Attribute } from 'models/attribute'
import { post, get, delete_ } from 'services/api/api_methods'

const mapperApi = {
  create: async (name: string, attributeSchemaUid: string) => {
    return await post('mapper/create', {
      name,
      attributeSchemaUid,
    }).then<Mapper>(async (response) => await response.json())
  },

  saveMapping: async (mapping: MappingItem) => {
    const formData = new FormData()
    formData.append('mapping', JSON.stringify(mapping))

    return await post('mapper/mapping/' + mapping.uid, formData)
  },

  deleteMapping: async (mapping: MappingItem) => {
    return await delete_('mapper/mapping/' + mapping.uid)
  },

  getMappers: async () => {
    return await get('mapper').then<Mapper[]>(async (response) => await response.json())
  },

  get: async (mapperUid: string) => {
    return await get('mapper/' + mapperUid).then<Mapper>(
      async (response) => await response.json(),
    )
  },

  getUnmappedValues: async (mapperUid: string) => {
    return await get('mapper/' + mapperUid + '/unmapped').then<string[]>(
      async (response) => await response.json(),
    )
  },

  // getForTag: async (tag: string) => {
  //   return await post('mapper/tag/' + tag).then<Mapper[]>(
  //     async (response) => await response.json(),
  //   )
  // },

  getMappings: async (mapperUid: string) => {
    return await get('mapper/' + mapperUid + '/mapping').then<MappingItem[]>(
      async (response) => await response.json(),
    )
  },

  getMapping: async (mappingUid: string) => {
    return await get('/mapper/mapping/' + mappingUid).then<MappingItem>(
      async (response) => await response.json(),
    )
  },

  getMappingAttributes: async (mapperUid: string) => {
    return await get('mapper/' + mapperUid + '/attributes').then<
      Array<Attribute<any, any>>
    >(async (response) => await response.json())
  },
}

export default mapperApi
