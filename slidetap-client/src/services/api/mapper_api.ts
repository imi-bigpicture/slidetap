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
import { delete_, get, post } from 'src/services/api/api_methods'

const mapperApi = {
  create: async (name: string, attributeSchemaUid: string) => {
    return await post('mappers/create', {
      name,
      attributeSchemaUid,
    }).then<Mapper>(async (response) => await response.json())
  },

  createGroup: async (group: MapperGroup) => {
    return await post('mappers/group/create', group,
    ).then<Mapper>(async (response) => await response.json())
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
    return await get('mappers/mapper').then<Mapper[]>(async (response) => await response.json())
  },

  get: async (mapperUid: string) => {
    return await get('mappers/mapper/' + mapperUid).then<Mapper>(
      async (response) => await response.json(),
    )
  },

  getUnmappedValues: async (mapperUid: string) => {
    return await get('mappers/mapper/' + mapperUid + '/unmapped').then<string[]>(
      async (response) => await response.json(),
    )
  },

  // getForTag: async (tag: string) => {
  //   return await post('mapper/tag/' + tag).then<Mapper[]>(
  //     async (response) => await response.json(),
  //   )
  // },

  getMappings: async (mapperUid: string) => {
    return await get('mappers/mapper/' + mapperUid + '/mapping').then<MappingItem[]>(
      async (response) => await response.json(),
    )
  },

  getMapping: async (mappingUid: string) => {
    return await get('mappers/mappings/mapping' + mappingUid).then<MappingItem>(
      async (response) => await response.json(),
    )
  },

  getMappingAttributes: async (mapperUid: string) => {
    return await get('mappers/mapper/' + mapperUid + '/attributes').then<
      Array<Attribute<AttributeValueTypes>>
    >(async (response) => await response.json())
  },

  getMapperGroups: async () => {
    return await get('mappers/groups').then<MapperGroup[]>(async (response) => await response.json())
  }

}

export default mapperApi
