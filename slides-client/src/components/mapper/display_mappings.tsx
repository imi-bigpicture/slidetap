import React, { useEffect, useState, ReactElement } from 'react'
import { Mapper, MappingItem } from 'models/mapper'
import mapperApi from 'services/api/mapper_api'
import { Table } from 'components/table'
import { Button } from '@mui/material'
import { TableItem } from 'models/table_item'
import EditMappingModal from './edit_mapping_modal'

interface DisplayMappingsProps {
    mapper: Mapper
}

export default function DisplayMappings (
    { mapper }: DisplayMappingsProps
): ReactElement {
    const [mappings, setMappings] = useState<MappingItem[]>([])
    const [editMappingModalOpen, setEditMappingModalOpen] = React.useState(false)
    const [isLoading, setIsLoading] = useState<boolean>(true)
    const [mappingUid, setMappingUid] = React.useState<string>()

    useEffect(() => {
        const getMappings = (): void => {
            mapperApi.getMappings(mapper.uid)
                .then(response => {
                    setMappings(response)
                    setIsLoading(false)
                })
                .catch(x => console.error('Failed to get items', x))
        }
        getMappings()
    }, [mapper.uid])
    const handleNewMappingClick = (event: React.MouseEvent): void => {
        setEditMappingModalOpen(true)
    }
    const handleOpenMappingClick = (mapping: TableItem): void => {
        setMappingUid(mapping.uid)
        setEditMappingModalOpen(true)
    }
    return (
        <React.Fragment>
            <Button onClick={handleNewMappingClick}>New mapping</Button>
            <Table
                columns={[
                    {
                        header: 'Expression',
                        accessorKey: 'expression'
                    },
                    {
                        header: 'Value',
                        accessorKey: 'displayValue'
                    }
                ]}
                data={mappings.map(mapping => {
                    return {
                        uid: mapping.uid,
                        expression: mapping.expression,
                        displayValue: mapping.value.displayValue
                    }
                })}
                rowsSelectable={false}
                onRowClick={handleOpenMappingClick}
                isLoading={isLoading}
            />
            <EditMappingModal
                open={editMappingModalOpen}
                setOpen={setEditMappingModalOpen}
                mappingUid={mappingUid}
                mapperUid={mapper.uid}
                attributeValueType={mapper.attributeValueType}
            />
        </React.Fragment>
    )
}
