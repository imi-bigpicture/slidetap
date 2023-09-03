import React, { useEffect, useState, ReactElement } from 'react'
import { Mapper, MappingItem } from 'models/mapper'
import mapperApi from 'services/api/mapper_api'
import { Table } from 'components/table'
import { Button } from '@mui/material'
import { TableItem } from 'models/table_item'
import EditMappingModal from './edit_mapping_modal'
import { Attribute } from 'models/attribute'

interface DisplayMappingAttributesProps {
  mapper: Mapper
}

export default function DisplayMappingAttributes({
  mapper,
}: DisplayMappingAttributesProps): ReactElement {
  const [attributes, setAttributes] = useState<Array<Attribute<any, any>>>([])
  // const [editMappingModalOpen, setEditMappingModalOpen] = React.useState(false)
  const [isLoading, setIsLoading] = useState<boolean>(true)

  useEffect(() => {
    const getMappingAttributes = (): void => {
      mapperApi
        .getMappingAttributes(mapper.uid)
        .then((response) => {
          setAttributes(response)
          setIsLoading(false)
        })
        .catch((x) => console.error('Failed to get items', x))
    }
    getMappingAttributes()
  }, [mapper.uid])
  return (
    <React.Fragment>
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
        // onRowClick={handleOpenMappingClick}
        isLoading={isLoading}
      />
      {/* <EditMappingModal
                open={editMappingModalOpen}
                setOpen={setEditMappingModalOpen}
                mappingUid={mappingUid}
                mapperUid={mapper.uid}
                attributeValueType={mapper.attributeValueType}
            /> */}
    </React.Fragment>
  )
}
