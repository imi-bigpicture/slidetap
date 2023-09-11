import React, { useEffect, useState, type ReactElement } from 'react'

import DisplayAttribute from 'components/attribute/display_attribute'
import { Dialog, Box, Button, Stack, TextField } from '@mui/material'
import Spinner from 'components/spinner'
import type { AttributeValueType } from 'models/attribute'
import type { MappingItem } from 'models/mapper'
import mapperApi from 'services/api/mapper_api'

interface EditMappingModalProps {
  open: boolean
  setOpen: React.Dispatch<React.SetStateAction<boolean>>
  mapperUid: string
  mappingUid: string | undefined
  attributeValueType: AttributeValueType
}

export default function EditMappingModal({
  open,
  setOpen,
  mapperUid,
  mappingUid,
  attributeValueType,
}: EditMappingModalProps): ReactElement {
  const [mapping, setMapping] = useState<MappingItem>()
  const [isLoading, setIsLoading] = useState<boolean>(true)

  useEffect(() => {
    if (mappingUid === undefined) {
      setIsLoading(false)
      return
    }
    const getMappings = (): void => {
      mapperApi
        .getMapping(mapperUid, mappingUid)
        .then((response) => {
          setMapping(response)
          setIsLoading(false)
        })
        .catch((x) => {console.error('Failed to get items', x)})
    }
    getMappings()
  }, [mapperUid, mappingUid])
  const handleClose = (): void => {
    setOpen(false)
  }
  const handleSave = (): void => {}
  return (
    <React.Fragment>
      {mapping !== undefined && (
        <Dialog onClose={handleClose} open={open}>
          <Spinner loading={isLoading}>
            <Box sx={{ m: 1, p: 1 }}>
              <TextField label="Expression" value={mapping.expression} />
              <DisplayAttribute attribute={mapping.value} />
              <Stack direction="row" spacing={2} justifyContent="center">
                <Button onClick={handleSave}>Save</Button>
                <Button onClick={handleClose}>Close</Button>
              </Stack>
            </Box>
          </Spinner>
        </Dialog>
      )}
    </React.Fragment>
  )
}
