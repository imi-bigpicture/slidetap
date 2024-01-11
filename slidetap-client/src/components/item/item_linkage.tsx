import type { Item, ItemReference } from 'models/items'
import React, { type ReactElement } from 'react'
import { Card, CardContent, Stack, TextField } from '@mui/material'

import { isImageItem, isObservationItem, isSampleItem } from 'models/helpers'
import DisplayItemReferences from './display_item_references'
import { ImageStatusStrings } from 'models/status'
import type { Action } from 'models/table_item'

interface ItemLinkageProps {
  item: Item
  action: Action
  handleItemOpen: (itemUid: string) => void
  setItem: (value: React.SetStateAction<Item | undefined>) => void
}

export default function ItemLinkage({
  item,
  action,
  handleItemOpen,
  setItem,
}: ItemLinkageProps): ReactElement {
  if (isSampleItem(item)) {
    const handleSampleParentsUpdate = (references: ItemReference[]): void => {
      const updatedItem = { ...item, parents: references }
      setItem(updatedItem)
    }
    const handleSampleChildrenUpdate = (references: ItemReference[]): void => {
      const updatedItem = { ...item, children: references }
      setItem(updatedItem)
    }
    return (
      <Card>
        <CardContent>
          <DisplayItemReferences
            title="Sampled from"
            action={action}
            schemas={item.schema.parents}
            references={item.parents}
            projectUid={item.projectUid}
            handleItemOpen={handleItemOpen}
            handleItemReferencesUpdate={handleSampleChildrenUpdate}
          />
          <Stack direction="column" spacing={1}>
            <DisplayItemReferences
              title="Sampled to"
              action={action}
              schemas={item.schema.children}
              references={item.children}
              projectUid={item.projectUid}
              handleItemOpen={handleItemOpen}
              handleItemReferencesUpdate={handleSampleParentsUpdate}
            />
          </Stack>
        </CardContent>
      </Card>
    )
  }
  if (isImageItem(item)) {
    const handleImageSamplesUpdate = (references: ItemReference[]): void => {
      const updatedItem = { ...item, samples: references }
      setItem(updatedItem)
    }
    return (
      <Card>
        <CardContent>
          <TextField label="Status" value={ImageStatusStrings[item.status]} />
          <DisplayItemReferences
            title="Image of"
            action={action}
            schemas={item.schema.parents}
            references={item.samples}
            projectUid={item.projectUid}
            handleItemOpen={handleItemOpen}
            handleItemReferencesUpdate={handleImageSamplesUpdate}
          />
        </CardContent>
      </Card>
    )
  }
  if (isObservationItem(item)) {
    const handleObservationItemsUpdate = (references: ItemReference[]): void => {
      const updatedItem = { ...item, items: references }
      setItem(updatedItem)
    }
    return (
      <Card>
        <CardContent>
          <DisplayItemReferences
            title="Observed on"
            action={action}
            schemas={item.schema.parents}
            references={[item.item]}
            projectUid={item.projectUid}
            handleItemOpen={handleItemOpen}
            handleItemReferencesUpdate={handleObservationItemsUpdate}
          />
        </CardContent>
      </Card>
    )
  }
  return <></>
}
