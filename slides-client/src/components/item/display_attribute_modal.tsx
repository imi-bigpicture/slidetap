import React, { useEffect, useState, ReactElement } from 'react'

import { Dialog, Box, Button, Stack } from '@mui/material'
import Spinner from 'components/spinner'
import attributeApi from 'services/api/attribute_api'
import { Attribute } from 'models/attribute'
import DisplayAttribute from 'components/attribute/display_attribute'
import { Mapping } from 'models/mapper'
import DisplayMapping from './display_mapping'

interface DisplayAttributeModalProp {
    attributeUid: string | undefined
    open: boolean
    setOpen: React.Dispatch<React.SetStateAction<boolean>>
}

export default function DisplayAttributeModal (
    { attributeUid, open, setOpen }: DisplayAttributeModalProp
): ReactElement {
    const [attribute, setAttribute] = React.useState<Attribute<any, any>>()
    const [mapping, setMapping] = React.useState<Mapping>()
    const [isLoading, setIsLoading] = useState<boolean>(true)

    useEffect(() => {
        const getAttribute = (): void => {
            if (attributeUid === undefined) {
                return
            }
            attributeApi.getAttribute(attributeUid)
                .then(attribute => {
                    setAttribute(attribute)
                    setIsLoading(false)
                }).catch(x => console.error('Failed to get items', x))
        }
        getAttribute()
    }, [attributeUid])

    useEffect(() => {
        const getMapping = (): void => {
            if (attributeUid === undefined) {
                return
            }
            attributeApi.getMapping(attributeUid)
                .then(mapping => {
                    setMapping(mapping)
                }).catch(x => console.error('Failed to get items', x))
        }
        getMapping()
    }, [attributeUid])

    const handleClose = (): void => {
        setOpen(false)
    }
    const handleSave = (): void => {

    }
    return (
        <React.Fragment>
            {attribute !== undefined &&
                <Dialog onClose={handleClose} open={open}>
                    <Spinner loading={isLoading}>
                        <Box sx={{ m: 1, p: 1 }}>
                            <DisplayAttribute attribute={attribute} />
                            {mapping !== undefined &&
                                <DisplayMapping mapping={mapping} />
                            }
                            <Stack direction="row" spacing={2} justifyContent="center">
                                <Button onClick={handleSave}>Save</Button>
                                <Button onClick={handleClose}>Close</Button>
                            </Stack>
                        </Box>
                    </Spinner>
                </Dialog>
            }
        </React.Fragment>

    )
}
