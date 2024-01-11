import React, { useEffect, type ReactElement } from 'react'

import type { ItemReference } from 'models/items'
import { Autocomplete, TextField, Stack, Chip } from '@mui/material'
import { Action } from 'models/table_item'
import itemApi from 'services/api/item_api'
import type { BaseItemSchema } from 'models/schema'
import { ArrowDropDownIcon } from '@mui/x-date-pickers'

interface DisplayItemReferencesProps {
  title: string
  action: Action
  schemas: BaseItemSchema[]
  references: ItemReference[]
  projectUid: string
  handleItemOpen: (itemUid: string) => void
  handleItemReferencesUpdate: (references: ItemReference[]) => void
}

export default function DisplayItemReferences({
  title,
  action,
  schemas,
  references,
  projectUid,
  handleItemOpen,
  handleItemReferencesUpdate,
}: DisplayItemReferencesProps): ReactElement {
  if (schemas.length === 0) {
    return <></>
  }
  const referencesBySchema: Record<string, ItemReference[]> = {}
  schemas.forEach((schema) => {
    referencesBySchema[schema.uid] = references.filter(
      (reference) => reference.schemaUid === schema.uid,
    )
  })
  return (
    <Stack direction="column" spacing={1}>
      {schemas.map((schema) => (
        <DisplayItemReferencesOfType
          key={schema.uid}
          title={title}
          editable={action !== Action.VIEW}
          schemaUid={schema.uid}
          schemaDisplayName={schema.displayName}
          references={referencesBySchema[schema.uid]}
          projectUid={projectUid}
          handleItemOpen={handleItemOpen}
          handleItemReferencesUpdate={handleItemReferencesUpdate}
        />
      ))}
    </Stack>
  )
}

interface DisplayItemReferencesOfTypeProps {
  title: string
  editable: boolean
  schemaUid: string
  schemaDisplayName: string
  references: ItemReference[]
  projectUid: string
  handleItemOpen: (itemUid: string) => void
  handleItemReferencesUpdate: (references: ItemReference[]) => void
}

function DisplayItemReferencesOfType({
  title,
  editable,
  schemaUid,
  schemaDisplayName,
  references,
  projectUid,
  handleItemOpen,
  handleItemReferencesUpdate,
}: DisplayItemReferencesOfTypeProps): ReactElement {
  const [items, setItems] = React.useState<ItemReference[]>([])

  useEffect(() => {
    itemApi
      .getOfSchema(schemaUid, projectUid)
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
      size="small"
      getOptionLabel={(option) => option.name}
      filterSelectedOptions
      popupIcon={editable ? <ArrowDropDownIcon /> : null}
      renderInput={(params) => (
        <TextField
          {...params}
          label={title + ' ' + schemaDisplayName}
          placeholder={editable ? 'Add ' + schemaDisplayName : undefined}
          size="small"
        />
      )}
      renderTags={(value) => (
        <Stack direction="row" spacing={1}>
          {value.map((option, index) => (
            <Chip
              key={index}
              label={option.name}
              onClick={() => {
                console.log('clicked', option)
                handleItemOpen(option.uid)
              }}
            />
          ))}
        </Stack>
      )}
      isOptionEqualToValue={(option, value) => option.uid === value.uid}
      onChange={(event, value) => {
        handleItemReferencesUpdate(value)
      }}
    />
  )
}
