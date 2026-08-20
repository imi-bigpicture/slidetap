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

import type {
  Mapper,
  MapperCreate,
  MapperGroup,
  MapperGroupCreate,
  MappingItem,
  MappingItemCreate,
} from 'src/models/mapper'
import { delete_, get, parseJsonResponse, post } from 'src/services/api/api_methods'

const mapperApi = {
  create: async (mapper: MapperCreate) => {
    const response = await post('mappers/create', mapper)
    return await parseJsonResponse<Mapper>(response)
  },

  update: async (mapper: Mapper) => {
    const response = await post('mappers/mapper/' + mapper.uid, mapper)
    return await parseJsonResponse<Mapper>(response)
  },

  delete: async (mapperUid: string) => {
    return await delete_('mappers/mapper/' + mapperUid)
  },

  createGroup: async (group: MapperGroupCreate) => {
    const response = await post('mappers/groups/create', group)
    return await parseJsonResponse<MapperGroup>(response)
  },

  createMapping: async (mapping: MappingItemCreate) => {
    const response = await post('mappers/mappings/create', mapping)
    return await parseJsonResponse<MappingItem>(response)
  },

  updateMapping: async (mapping: MappingItem) => {
    const response = await post('mappers/mappings/mapping/' + mapping.uid, mapping)
    return await parseJsonResponse<MappingItem>(response)
  },

  deleteMapping: async (mappingUid: string) => {
    return await delete_('mappers/mappings/mapping/' + mappingUid)
  },

  getMappers: async () => {
    const response = await get('mappers')
    return await parseJsonResponse<Mapper[]>(response)
  },

  get: async (mapperUid: string) => {
    const response = await get('mappers/mapper/' + mapperUid)
    return await parseJsonResponse<Mapper>(response)
  },

  getMappings: async (mapperUid: string) => {
    const response = await get('mappers/mapper/' + mapperUid + '/mapping')
    return await parseJsonResponse<MappingItem[]>(response)
  },

  getMapping: async (mappingUid: string) => {
    const response = await get('mappers/mappings/mapping/' + mappingUid)
    return await parseJsonResponse<MappingItem>(response)
  },

  getMapperGroups: async () => {
    const response = await get('mappers/groups')
    return await parseJsonResponse<MapperGroup[]>(response)
  },

  setMappersInGroup: async (groupUid: string, mapperUids: string[]) => {
    const response = await post('mappers/groups/' + groupUid + '/mappers', mapperUids)
    return await parseJsonResponse<MapperGroup>(response)
  },
}

export default mapperApi
