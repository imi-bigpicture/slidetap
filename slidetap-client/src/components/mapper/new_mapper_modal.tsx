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

import React, { type ReactElement } from 'react'

import {
  Box,
  Button,
  Dialog,
  MenuItem,
  Select,
  Stack,
  TextField,
} from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import Spinner from 'src/components/spinner'
import { useError } from 'src/contexts/error/error_context'
import { Mapper } from 'src/models/mapper'
import mapperApi from 'src/services/api/mapper_api'
import schemaApi from 'src/services/api/schema_api'
import { queryKeys } from 'src/services/query_keys'

interface NewMapperModalProp {
  open: boolean
  setOpen: React.Dispatch<React.SetStateAction<boolean>>
  /** Mapper to edit. If not set a new mapper is created. */
  mapper?: Mapper
}

export default function NewMapperModal({
  open,
  setOpen,
  mapper,
}: NewMapperModalProp): ReactElement {
  const [attributeSchemaUid, setAttributeSchemaUid] = React.useState<string>()
  const [mapperName, setMapperName] = React.useState<string>('New mapper')
  const { showError } = useError()
  const queryClient = useQueryClient()
  const attributeSchemasQuery = useQuery({
    queryKey: queryKeys.schema.attributes(),
    queryFn: async () => {
      return await schemaApi.getAttributeSchemas()
    },
  })

  // Reset the form to the mapper being edited, or to the first attribute schema.
  React.useEffect(() => {
    if (!open) {
      return
    }
    setMapperName(mapper?.name ?? 'New mapper')
    setAttributeSchemaUid(
      mapper?.attributeSchemaUid ?? attributeSchemasQuery.data?.[0]?.uid,
    )
  }, [open, mapper, attributeSchemasQuery.data])

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (attributeSchemaUid === undefined) {
        throw new Error('No attribute schema selected')
      }
      if (mapper !== undefined) {
        return await mapperApi.update({ ...mapper, name: mapperName })
      }
      return await mapperApi.create({ name: mapperName, attributeSchemaUid })
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.mapper.all })
      setOpen(false)
    },
    onError: (error) => {
      showError('Failed to save mapper', error)
    },
  })

  const handleClose = (): void => {
    setOpen(false)
  }

  return (
    <React.Fragment>
      <Dialog onClose={handleClose} open={open}>
        <Spinner loading={attributeSchemasQuery.isLoading}>
          <Box sx={{ m: 1, p: 1 }}>
            <Stack spacing={1}>
              <Select
                label="Attribute"
                value={attributeSchemaUid ?? ''}
                // The backend only updates the name, so the schema is fixed on edit.
                disabled={mapper !== undefined}
                onChange={(event) => {
                  setAttributeSchemaUid(event.target.value)
                }}
              >
                {(attributeSchemasQuery.data ?? []).map((schema) => (
                  <MenuItem key={schema.uid} value={schema.uid}>
                    {schema.displayName}
                  </MenuItem>
                ))}
              </Select>
              <TextField
                label="Name"
                value={mapperName}
                onChange={(event) => {
                  setMapperName(event.target.value)
                }}
              />
              <Stack direction="row" spacing={1} sx={{ justifyContent: 'center' }}>
                <Button
                  onClick={() => saveMutation.mutate()}
                  disabled={attributeSchemaUid === undefined || saveMutation.isPending}
                >
                  Save
                </Button>
                <Button onClick={handleClose}>Close</Button>
              </Stack>
            </Stack>
          </Box>
        </Spinner>
      </Dialog>
    </React.Fragment>
  )
}
