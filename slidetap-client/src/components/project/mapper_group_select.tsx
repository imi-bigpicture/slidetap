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

import { Autocomplete, TextField } from '@mui/material'
import React from 'react'
import { MapperGroup } from 'src/models/mapper'

interface MapperGroupSelectProps {
  selectedMapperGroups: string[]
  availableMapperGroups: MapperGroup[]
  setSelectedMapperGroups: (mapperGroups: string[]) => void
}

export default function MapperGroupSelect({
  selectedMapperGroups,
  availableMapperGroups,
  setSelectedMapperGroups,
}: MapperGroupSelectProps): React.ReactElement {
  const value = selectedMapperGroups
    .map((uid) => availableMapperGroups.find((group) => group.uid === uid))
    .filter((group) => group !== undefined)

  return (
    <Autocomplete
      multiple
      value={value}
      options={availableMapperGroups}
      getOptionLabel={(option) => option.name}
      renderInput={(params) => (
        <TextField {...params} label={'Mapper groups'} size="small" />
      )}
      onChange={(_, newValue) => {
        setSelectedMapperGroups(newValue.map((group) => group.uid))
      }}
    />
  )
}
