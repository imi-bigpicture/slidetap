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

import { useQuery } from '@tanstack/react-query'
import { BasicTable } from 'components/table/basic_table'
import type { Mapper } from 'models/mapper'
import React from 'react'
import mapperApi from 'services/api/mapper_api'

interface DisplayMappingAttributesProps {
  mapper: Mapper
}

export default function DisplayMappingAttributes({
  mapper,
}: DisplayMappingAttributesProps): React.ReactElement {
  // const [editMappingModalOpen, setEditMappingOpen] = React.useState(false)
  const attributesQuery = useQuery({
    queryKey: ['mappingAttributes', mapper.uid],
    queryFn: async () => {
      return await mapperApi.getMappingAttributes(mapper.uid)
    },
    select: (data) => {
      return data.map((attribute) => {
        return {
          uid: attribute.uid,
          displayValue: attribute.displayValue,
        }
      })
    },
  })

  return (
    <BasicTable
      columns={[
        {
          header: 'Value',
          accessorKey: 'displayValue',
        },
      ]}
      data={attributesQuery.data ?? []}
      rowsSelectable={false}
      // onRowAction={handleOpenMappingClick}
      isLoading={attributesQuery.isLoading}
    />
  )
}
