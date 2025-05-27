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
