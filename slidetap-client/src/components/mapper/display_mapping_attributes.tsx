import React, { useEffect, useState, type ReactElement } from 'react'
import type { Mapper } from 'models/mapper'
import mapperApi from 'services/api/mapper_api'
import { Table } from 'components/table'
import type { Attribute } from 'models/attribute'

interface DisplayMappingAttributesProps {
  mapper: Mapper
}

export default function DisplayMappingAttributes({
  mapper,
}: DisplayMappingAttributesProps): ReactElement {
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
    <Table
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
