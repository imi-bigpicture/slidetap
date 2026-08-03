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

import { Autocomplete, Box, Button, Dialog, Stack, TextField } from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import React, { type ReactElement } from 'react'
import Spinner from 'src/components/spinner'
import { useError } from 'src/contexts/error/error_context'
import { Mapper, MapperGroup } from 'src/models/mapper'
import mapperApi from 'src/services/api/mapper_api'
import { queryKeys } from 'src/services/query_keys'

interface MapperGroupMappersModalProps {
  open: boolean
  setOpen: React.Dispatch<React.SetStateAction<boolean>>
  group: MapperGroup
}

export default function MapperGroupMappersModal({
  open,
  setOpen,
  group,
}: MapperGroupMappersModalProps): ReactElement {
  const [selectedMappers, setSelectedMappers] = React.useState<string[]>(group.mappers)
  const { showError } = useError()
  const queryClient = useQueryClient()

  const mappersQuery = useQuery({
    queryKey: queryKeys.mapper.all,
    queryFn: async () => {
      return await mapperApi.getMappers()
    },
  })

  React.useEffect(() => {
    setSelectedMappers(group.mappers)
  }, [group])

  const saveMutation = useMutation({
    mutationFn: async () => {
      return await mapperApi.setMappersInGroup(group.uid, selectedMappers)
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.mapperGroup.all })
      setOpen(false)
    },
    onError: (error) => {
      showError('Failed to save mappers in group', error)
    },
  })

  const value = selectedMappers
    .map((uid) => mappersQuery.data?.find((mapper) => mapper.uid === uid))
    .filter((mapper): mapper is Mapper => mapper !== undefined)

  return (
    <Dialog onClose={() => setOpen(false)} open={open} fullWidth>
      <Spinner loading={mappersQuery.isLoading}>
        <Box sx={{ m: 1, p: 1 }}>
          <Stack spacing={1}>
            <Autocomplete
              multiple
              value={value}
              options={mappersQuery.data ?? []}
              getOptionLabel={(mapper) => mapper.name}
              renderInput={(params) => (
                <TextField {...params} label={`Mappers in ${group.name}`} />
              )}
              onChange={(_, newValue) => {
                setSelectedMappers(newValue.map((mapper) => mapper.uid))
              }}
            />
            <Stack direction="row" spacing={1} sx={{ justifyContent: 'center' }}>
              <Button
                onClick={() => saveMutation.mutate()}
                disabled={saveMutation.isPending}
              >
                Save
              </Button>
              <Button onClick={() => setOpen(false)}>Close</Button>
            </Stack>
          </Stack>
        </Box>
      </Spinner>
    </Dialog>
  )
}
