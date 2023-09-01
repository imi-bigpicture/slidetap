import React, { useEffect, useState, ReactElement } from 'react'
import { useNavigate } from 'react-router-dom'
import mapperApi from 'services/api/mapper_api'
import { Mapper } from 'models/mapper'
import { Table } from 'components/table'
import { Button } from '@mui/material'
import NewMapperModal from './new_mapper_modal'
import { TableItem } from 'models/table_item'

export default function DisplayMappers (): ReactElement {
    const [mappers, setMappers] = useState<Mapper[]>([])
    const [newMapperModalOpen, setNewMapperModalOpen] = React.useState(false)
    const [isLoading, setIsLoading] = useState<boolean>(true)
    const navigate = useNavigate()

    const getMappers = (): void => {
        mapperApi.getMappers()
            .then(
                mappers => {
                    setMappers(mappers)
                    setIsLoading(false)
                }
            )
            .catch(x => console.error('Failed to get mappers', x))
    }

    useEffect(() => {
        getMappers()
        // const intervalId = setInterval(() => {
        //     getMappers()
        // }, 2000)
        // return () => clearInterval(intervalId)
    }, [])

    const handleNewMapperClick = (event: React.MouseEvent): void => {
        setNewMapperModalOpen(true)
    }
    const navigateToMapper = (mapper: TableItem): void => {
        return navigate(`/mapping/${mapper.uid}`)
    }

    return (
        <React.Fragment>
            <Button onClick={handleNewMapperClick}>New mapper</Button>
            <Table
                columns={[
                    {
                        header: 'Name',
                        accessorKey: 'name'
                    },
                    {
                        header: 'Attribute',
                        accessorKey: 'attributeSchemaName'
                    }
                ]}
                data={mappers.map(mapper => {
                    return {
                        uid: mapper.uid,
                        name: mapper.name,
                        attributeSchemaName: mapper.attributeSchemaName
                    }
                })}
                rowsSelectable={false}
                onRowClick={navigateToMapper}
                isLoading={isLoading}
            />
            <NewMapperModal
                open={newMapperModalOpen}
                setOpen={setNewMapperModalOpen}
            />
        </React.Fragment>
    )
}
