//    Copyright 2024 SECTRA AB
//
//    Licensed under the Apache License, Version 2.0 (the "License");
//    you may not use this file except in compliance with the License.
//    You may obtain a copy of the License at
//
//        http://www.apache.org/licenses/LICENSE-2.0
//
//    Unless required by applicable law or agreed to in writing, software
//    distributed under the License is distributed on an "AS IS" BASIS,
//    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//    See the License for the specific language governing permissions and
//    limitations under the License.

import React, { useEffect, useState, type ReactElement } from 'react'

import { Dialog, Box, Button, Stack, Select, MenuItem, TextField } from '@mui/material'
import Spinner from 'components/spinner'
import schemaApi from 'services/api/schema_api'
import type { AttributeSchema } from 'models/schema'
import mapperApi from 'services/api/mapper_api'

interface NewMapperModalProp {
  open: boolean
  setOpen: React.Dispatch<React.SetStateAction<boolean>>
}

export default function NewMapperModal({
  open,
  setOpen,
}: NewMapperModalProp): ReactElement {
  const [attributeSchemas, setAttributeSchemas] = React.useState<AttributeSchema[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [attributeSchemaUid, setAttributeSchemaUid] = React.useState<string>()
  const [mapperName, setMapperName] = React.useState<string>('New mapper')
  useEffect(() => {
    const getAttributeSchemas = (): void => {
      schemaApi
        .getAttributeSchemas('752ee40c-5ebe-48cf-b384-7001239ee70d')
        .then((schemas) => {
          setAttributeSchemas(schemas)
          if (schemas.length > 0) {
            setAttributeSchemaUid(schemas[0].uid)
          }
          setLoading(false)
        })
        .catch((x) => {console.error('Failed to get schemas', x)})
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
    mapperApi
      .create(mapperName, attributeSchemaUid)
      .then((response) => {setOpen(false)})
      .catch((x) => {console.error('Failed to get save mapper', x)})
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
              label="Attribute"
              value={attributeSchemaUid}
              onChange={(event) => { setAttributeSchemaUid(event.target.value) }}
            >
              {attributeSchemas.map((schema) => (
                <MenuItem key={schema.uid} value={schema.uid}>
                  {schema.displayName}
                </MenuItem>
              ))}
            </Select>
            <TextField
              label="Name"
              value={mapperName}
              onChange={(event) => { setMapperName(event.target.value) }}
            />
            <Stack direction="row" spacing={2} justifyContent="center">
              <Button onClick={handleSave}>Save</Button>
              <Button onClick={handleClose}>Close</Button>
            </Stack>
          </Box>
        </Spinner>
      </Dialog>
    </React.Fragment>
  )
}
