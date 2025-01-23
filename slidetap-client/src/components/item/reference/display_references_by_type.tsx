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

import { Autocomplete, Chip, CircularProgress, TextField } from '@mui/material'
import { ArrowDropDownIcon } from '@mui/x-date-pickers'
import { useQuery } from '@tanstack/react-query'
import React, { type ReactElement } from 'react'
import { ItemSchema } from 'src/models/schema/item_schema'
import itemApi from 'src/services/api/item_api'

interface DisplayItemReferencesOfTypeProps {
  title: string
  editable: boolean
  schema: ItemSchema
  references: string[]
  datasetUid: string
  batchUid?: string
  handleItemOpen: (itemUid: string) => void
  handleItemReferencesUpdate: (references: string[]) => void
  minReferences?: number
  maxReferences?: number
}

export default function DisplayItemReferencesOfType({
  title,
  editable,
  schema,
  references,
  datasetUid,
  batchUid,
  handleItemOpen,
  handleItemReferencesUpdate,
  minReferences,
  maxReferences,
}: DisplayItemReferencesOfTypeProps): ReactElement {
  const itemQuery = useQuery({
    queryKey: ['items', schema.uid, datasetUid, batchUid],
    queryFn: async () => {
      return await itemApi.getReferences(schema.uid, datasetUid, batchUid)
    },
  })
  if (itemQuery.isLoading || itemQuery.data === undefined) {
    return <CircularProgress />
  }
  const referencesOfSchema = references
    .map((reference) => itemQuery.data[reference])
    .filter((item) => item !== undefined)
  return (
    <Autocomplete
      multiple
      value={referencesOfSchema}
      options={Object.values(itemQuery.data)}
      readOnly={!editable}
      autoComplete={true}
      autoHighlight={true}
      fullWidth={true}
      limitTags={3}
      size="small"
      getOptionLabel={(option) => option.identifier}
      filterSelectedOptions
      popupIcon={editable ? <ArrowDropDownIcon /> : null}
      renderInput={(params) => (
        <TextField
          {...params}
          label={title}
          placeholder={editable ? 'Add ' + schema.displayName : undefined}
          size="small"
          error={
            (minReferences !== null &&
              minReferences !== undefined &&
              referencesOfSchema.length < minReferences) ||
            (maxReferences !== null &&
              maxReferences !== undefined &&
              referencesOfSchema.length > maxReferences)
          }
        />
      )}
      renderTags={(value, getTagProps) => (
        <React.Fragment>
          {value.map((option, index) => {
            const { key, ...other } = getTagProps({ index })
            return (
              <Chip
                key={key}
                {...other}
                label={option.identifier}
                onClick={() => {
                  handleItemOpen(option.uid)
                }}
              />
            )
          })}
        </React.Fragment>
      )}
      isOptionEqualToValue={(option, value) => option.uid === value.uid}
      onChange={(_, value) => {
        handleItemReferencesUpdate(value.map((item) => item.uid))
      }}
    />
  )
}
