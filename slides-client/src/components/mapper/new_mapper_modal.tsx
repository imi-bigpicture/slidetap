import React, { useEffect, useState, ReactElement } from 'react'

import { Dialog, Box, Button, Stack, Select, MenuItem, TextField } from '@mui/material'
import Spinner from 'components/spinner'
import attributeApi from 'services/api/attribute_api'
import { AttributeSchema } from 'models/schema'
import mapperApi from 'services/api/mapper_api'

interface NewMapperModalProp {
    open: boolean
    setOpen: React.Dispatch<React.SetStateAction<boolean>>
}

export default function NewMapperModal (
    { open, setOpen }: NewMapperModalProp
): ReactElement {
    const [attributeSchemas, setAttributeSchemas] = React.useState<AttributeSchema[]>([])
    const [loading, setLoading] = useState<boolean>(true)
    const [attributeSchemaUid, setAttributeSchemaUid] = React.useState<string>()
    const [mapperName, setMapperName] = React.useState<string>('New mapper')
    useEffect(() => {
        const getAttributeSchemas = (): void => {
            attributeApi.getSchemas('752ee40c-5ebe-48cf-b384-7001239ee70d')
                .then(schemas => {
                    setAttributeSchemas(schemas)
                    if (schemas.length > 0) {
                        setAttributeSchemaUid(schemas[0].uid)
                    }
                    setLoading(false)
                }).catch(x => console.error('Failed to get schemas', x))
        }
        getAttributeSchemas()
    }, [])

    const handleClose = (): void => {
        setOpen(false)
    }
    const handleSave = (): void => {
        if (mapperName === undefined || attributeSchemaUid === undefined) {
            throw new Error()
        }
        mapperApi.create(mapperName, attributeSchemaUid)
            .then(response => setOpen(false))
            .catch(x => console.error('Failed to get save mapper', x))
    }

    if (attributeSchemaUid === undefined) {
        return <></>
    }
    return (
        <React.Fragment>
            <Dialog onClose={handleClose} open={open}>
                <Spinner loading={loading}>
                    <Box sx={{ m: 1, p: 1 }}>
                        <Select
                            label='Attribute'
                            value={attributeSchemaUid}
                            onChange={
                                event => setAttributeSchemaUid(event.target.value)
                            }
                        >
                            {attributeSchemas.map(schema => (
                                <MenuItem
                                    key={schema.uid}
                                    value={schema.uid}>
                                    {schema.schemaDisplayName}
                                </MenuItem>
                            ))}
                        </Select>
                        <TextField
                            label='Name'
                            value={mapperName}
                            onChange={
                                event => setMapperName(event.target.value)
                            }
                        />
                        <Stack direction="row" spacing={2} justifyContent="center">
                            <Button onClick={handleSave}>Save</Button>
                            <Button onClick={handleClose}>Close</Button>
                        </Stack>
                    </Box>
                </Spinner>

            </Dialog>
        </React.Fragment >

    )
}
