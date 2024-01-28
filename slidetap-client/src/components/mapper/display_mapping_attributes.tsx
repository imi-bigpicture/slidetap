import { BasicTable } from 'components/table'
import type { Attribute } from 'models/attribute'
import type { Mapper } from 'models/mapper'
import React, { useEffect, useState } from 'react'
import mapperApi from 'services/api/mapper_api'

interface DisplayMappingAttributesProps {
  mapper: Mapper
}

export default function DisplayMappingAttributes({
  mapper,
}: DisplayMappingAttributesProps): React.ReactElement {
  const [attributes, setAttributes] = useState<Array<Attribute<any, any>>>([])
  // const [editMappingModalOpen, setEditMappingOpen] = React.useState(false)
  const [isLoading, setIsLoading] = useState<boolean>(true)

  useEffect(() => {
    const getMappingAttributes = (): void => {
      mapperApi
        .getMappingAttributes(mapper.uid)
        .then((response) => {
          setAttributes(response)
          setIsLoading(false)
        })
        .catch((x) => {
          console.error('Failed to get items', x)
        })
    }
    getMappingAttributes()
  }, [mapper.uid])
  return (
    <BasicTable
      columns={[
        {
          header: 'Value',
          accessorKey: 'displayValue',
        },
      ]}
      data={attributes.map((attribute) => {
        return {
          uid: attribute.uid,
          displayValue: attribute.displayValue,
        }
      })}
      rowsSelectable={false}
      // onRowAction={handleOpenMappingClick}
      isLoading={isLoading}
    />
  )
}
