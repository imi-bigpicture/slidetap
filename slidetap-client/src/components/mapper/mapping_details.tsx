import React, { useEffect, useState, type ReactElement } from 'react'
import mappingApi from 'services/api/mapper_api'
import {
  Button,
  Card,
  CardContent,
  CardActions,
  CardHeader,
  Stack,
  TextField,
} from '@mui/material'
import Spinner from 'components/spinner'
import type { Attribute } from 'models/attribute'
import Grid from '@mui/material/Unstable_Grid2' // Grid version 2
import NestedAttributeDetails from '../attribute/nested_attribute_details'
import type { MappingItem } from 'models/mapper'
import DisplayAttribute from 'components/attribute/display_attribute'

interface MappingDetailsProps {
  mappingUid: string | undefined
  setOpen: React.Dispatch<React.SetStateAction<boolean>>
}

export default function MappingDetails({
  mappingUid,
  setOpen,
}: MappingDetailsProps): ReactElement {
  const [currentMappingUid, setCurrentMappingUid] = useState<string | undefined>(
    mappingUid,
  )
  const [mapping, setMapping] = useState<MappingItem>()
  const [openedAttributes, setOpenedAttributes] = useState<Array<Attribute<any, any>>>(
    [],
  )
  const [isLoading, setIsLoading] = useState<boolean>(true)

  const getMapping = (mappingUid: string): void => {
    mappingApi
      .getMapping(mappingUid)
      .then((responseMapping) => {
        console.log('got mapping', responseMapping)
        setOpenedAttributes([])
        setMapping(responseMapping)
        setIsLoading(false)
      })
      .catch((x) => {
        console.error('Failed to get items', x)
      })
  }

  useEffect(() => {
    if (currentMappingUid === undefined) {
      return
    }
    getMapping(currentMappingUid)
  }, [currentMappingUid])

  useEffect(() => {
    if (mappingUid === undefined) {
      return
    }
    setCurrentMappingUid(mappingUid)
  }, [mappingUid])

  if (mapping === undefined) {
    return <></>
  }

  const handleAttributeOpen = (attribute: Attribute<any, any>): void => {
    console.log('handling opening child object attribute', attribute)
    setOpenedAttributes([...openedAttributes, attribute])
  }

  const handleClose = (): void => {
    setOpen(false)
  }
  const handleSave = (): void => {}

  return (
    <Spinner loading={isLoading}>
      <Card>
        <CardHeader title="Mapping" />
        <CardContent>
          <Grid container spacing={2}>
            <Grid xs={12}>
              {openedAttributes.length === 0 && (
                <Stack spacing={2} direction={'column'}>
                  <TextField label="Expression" value={mapping.expression} />
                  <Stack spacing={2}>
                    <DisplayAttribute
                      attribute={mapping.attribute}
                      handleAttributeOpen={handleAttributeOpen}
                    />
                  </Stack>
                </Stack>
              )}
              {openedAttributes.length > 0 && (
                <NestedAttributeDetails
                  openedAttributes={openedAttributes}
                  setOpenedAttributes={setOpenedAttributes}
                  handleAttributeOpen={handleAttributeOpen}
                />
              )}
            </Grid>
          </Grid>
        </CardContent>
        <CardActions disableSpacing>
          <Button onClick={handleSave}>Save</Button>
          <Button onClick={handleClose}>Close</Button>
        </CardActions>
      </Card>
    </Spinner>
  )
}
