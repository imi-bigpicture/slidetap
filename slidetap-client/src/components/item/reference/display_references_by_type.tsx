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

import React, { useEffect, type ReactElement } from 'react'

import { Autocomplete, Chip, TextField } from '@mui/material'
import { ArrowDropDownIcon } from '@mui/x-date-pickers'
import type { ItemReference } from 'models/item'
import itemApi from 'services/api/item_api'

interface DisplayItemReferencesOfTypeProps {
  title: string
  editable: boolean
  schemaUid: string
  schemaDisplayName: string
  references: ItemReference[]
  projectUid: string
  handleItemOpen: (itemUid: string) => void
  handleItemReferencesUpdate: (references: ItemReference[]) => void
  minReferences?: number
  maxReferences?: number
}

export default function DisplayItemReferencesOfType({
  title,
  editable,
  schemaUid,
  schemaDisplayName,
  references,
  projectUid,
  handleItemOpen,
  handleItemReferencesUpdate,
  minReferences,
  maxReferences,
}: DisplayItemReferencesOfTypeProps): ReactElement {
  const [items, setItems] = React.useState<ItemReference[]>([])

  useEffect(() => {
    itemApi
      .getReferences(schemaUid, projectUid)
      .then((items) => {
        setItems(items)
      })
      .catch((x) => {
        console.error('Failed to get items', x)
      })
  }, [schemaUid, projectUid])
  return (
    <Autocomplete
      multiple
      value={references}
      options={items}
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
          placeholder={editable ? 'Add ' + schemaDisplayName : undefined}
          size="small"
          error={
            (minReferences !== null &&
              minReferences !== undefined &&
              references.length < minReferences) ||
            (maxReferences !== null &&
              maxReferences !== undefined &&
              references.length > maxReferences)
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
      onChange={(event, value) => {
        handleItemReferencesUpdate(value)
      }}
    />
  )
}
