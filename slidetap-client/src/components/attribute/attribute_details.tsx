import React, { useEffect, useState, type ReactElement } from 'react'

import { Dialog, Box, Button, Stack, Breadcrumbs } from '@mui/material'
import Spinner from 'components/spinner'
import attributeApi from 'services/api/attribute_api'
import type { Attribute } from 'models/attribute'
import DisplayAttribute from 'components/attribute/display_attribute'
import type { Mapping } from 'models/mapper'
import DisplayMapping from '../item/display_mapping'
import { Card, CardContent, CardHeader, CardActions, Link } from '@mui/material'
import Grid from '@mui/material/Unstable_Grid2' // Grid version 2

interface AttributeDetailsProp {
  attributeUid: string | undefined
  setOpen: React.Dispatch<React.SetStateAction<boolean>>
}

export default function AttributeDetails({
  attributeUid,
  setOpen,
}: AttributeDetailsProp): ReactElement {
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [attributes, setAttributes] = useState<Array<Attribute<any, any>>>([])

  const getAttribute = (attributeUid?: string, clear: boolean): void => {
    if (attributeUid === undefined) {
      return
    }
    attributeApi
      .getAttribute(attributeUid)
      .then((attribute) => {
        if (clear) {
          setAttributes([attribute])
        } else {
          setAttributes([...attributes, attribute])
        }

        setIsLoading(false)
      })
      .catch((x) => {console.error('Failed to get items', x)})
  }

  useEffect(() => {
    console.log("opening attribute", attributeUid, attributes)
    getAttribute(attributeUid, true)
  }, [attributeUid])

  const handleChangeAttribute = (attributeUid: string): void => {
    console.log("handling opening child object attribute", attributeUid)
    const parentAttribute = attributes.findIndex((attribute) => attribute.uid === attributeUid)
    if (parentAttribute === -1) {
      getAttribute(attributeUid, false )
    } else {
      setAttributes(attributes.slice(0, parentAttribute + 1))
    }
  }

  const handleClose = (): void => {
    setOpen(false)
  }
  const handleSave = (): void => { }

  if (attributes.length === 0) {
    return <></>
  }
  return (
    <Spinner loading={isLoading}>
      <Card>
        <CardHeader
          title={"Attribute details" }>
        </CardHeader>
        <CardContent>
          <Breadcrumbs aria-label="breadcrumb">
            {attributes.map((attribute) => {
              return (
                <Link
                  key={attribute.uid}
                  onClick={() => handleChangeAttribute(attribute.uid)}
                >
                  {attribute.schema.displayName}
                </Link>
              )
            })}
          </Breadcrumbs>
          <Grid container spacing={2}>
            <Grid>
              <DisplayAttribute
                attribute={attributes.slice(-1)[0]}
                handleChangeAttribute={handleChangeAttribute}
                />
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
