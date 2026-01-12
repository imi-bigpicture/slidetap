//    Copyright 2024 SECTRA AB
//
//    Licensed under the Apache License, Version 2.0 (the "License");
//    you may not use this file except in compliance with the License.
//    You may obtain a copy of the License at
//
//        http://www.apache.org/licenses/LICENSE-2.0
//
//    Unless required by applicable law or agreed to in writing, software
//    distributed under the License is distributed on an "AS IS" BASIS,
//    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//    See the License for the specific language governing permissions and
//    limitations under the License.

import type { Attribute, AttributeValueTypes } from 'src/models/attribute'
import type { Mapper, MapperGroup, MappingItem } from 'src/models/mapper'
import { delete_, get, parseJsonResponse, post } from 'src/services/api/api_methods'

const mapperApi = {
  create: async (name: string, attributeSchemaUid: string) => {
    const response = await post('mappers/create', {
      name,
      attributeSchemaUid,
    })
    return await parseJsonResponse<Mapper>(response)
  },

  createGroup: async (group: MapperGroup) => {
    const response = await post('mappers/group/create', group)
    return await parseJsonResponse<Mapper>(response)
  },

  saveMapping: async (mapping: MappingItem) => {
    const formData = new FormData()
    formData.append('mapping', JSON.stringify(mapping))
    return await post('mappers/mappings/mapping' + mapping.uid, formData)
  },

  deleteMapping: async (mapping: MappingItem) => {
    return await delete_('mappers/mappings/mapping' + mapping.uid)
  },

  getMappers: async () => {
    const response = await get('mappers/mapper')
    return await parseJsonResponse<Mapper[]>(response)
  },

  get: async (mapperUid: string) => {
    const response = await get('mappers/mapper/' + mapperUid)
    return await parseJsonResponse<Mapper>(response)
  },

  getUnmappedValues: async (mapperUid: string) => {
    const response = await get('mappers/mapper/' + mapperUid + '/unmapped')
    return await parseJsonResponse<string[]>(response)
  },

  getMappings: async (mapperUid: string) => {
    const response = await get('mappers/mapper/' + mapperUid + '/mapping')
    return await parseJsonResponse<MappingItem[]>(response)
  },

  getMapping: async (mappingUid: string) => {
    const response = await get('mappers/mappings/mapping' + mappingUid)
    return await parseJsonResponse<MappingItem>(response)
  },

  getMappingAttributes: async (mapperUid: string) => {
    const response = await get('mappers/mapper/' + mapperUid + '/attributes')
    return await parseJsonResponse<Array<Attribute<AttributeValueTypes>>>(response)
  },

  getMapperGroups: async () => {
    const response = await get('mappers/groups')
    return await parseJsonResponse<MapperGroup[]>(response)
  }
}

export default mapperApi
