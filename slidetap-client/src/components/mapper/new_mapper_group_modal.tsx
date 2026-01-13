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
  Checkbox,
  Dialog,
  FormControlLabel,
  Stack,
  TextField,
} from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import Spinner from 'src/components/spinner'
import { useError } from 'src/contexts/error/error_context'
import mapperApi from 'src/services/api/mapper_api'
import { queryKeys } from 'src/services/query_keys'

interface NewMapperGroupModalProp {
  open: boolean
  setOpen: React.Dispatch<React.SetStateAction<boolean>>
}

export default function NewMapperGroupModal({
  open,
  setOpen,
}: NewMapperGroupModalProp): ReactElement {
  const [groupName, setGroupName] = React.useState<string>('New mapper group')
  const [defaultEnabled, setDefaultEnabled] = React.useState<boolean>(false)
  const { showError } = useError()

  const mapperQuery = useQuery({
    queryKey: queryKeys.mapper.list(),
    queryFn: async () => {
      return await mapperApi.getMappers()
    },
  })

  const handleClose = (): void => {
    setOpen(false)
  }
  const handleSave = (): void => {
    mapperApi
      .createGroup({
        uid: '',
        name: groupName,
        defaultEnabled: defaultEnabled,
        mappers: [],
      })
      .then(() => {
        setOpen(false)
      })
      .catch((error) => {
        showError('Failed to save mapper group', error)
      })
  }

  return (
    <React.Fragment>
      <Dialog onClose={handleClose} open={open}>
        <Spinner loading={mapperQuery.isLoading}>
          <Box sx={{ m: 1, p: 1 }}>
            <TextField
              label="Name"
              value={groupName}
              onChange={(event) => {
                setGroupName(event.target.value)
              }}
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={defaultEnabled}
                  onChange={(event) => setDefaultEnabled(event.target.checked)}
                />
              }
              label="Default enabled"
            />
            <Stack direction="row" spacing={1} justifyContent="center">
              <Button onClick={handleSave}>Save</Button>
              <Button onClick={handleClose}>Close</Button>
            </Stack>
          </Box>
        </Spinner>
      </Dialog>
    </React.Fragment>
  )
}
