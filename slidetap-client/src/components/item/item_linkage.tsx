import type { Item } from 'models/items'
import React, { type ReactElement } from 'react'
import { TextField } from '@mui/material'

import { isImageItem, isObservationItem, isSampleItem } from 'models/helpers'
import DisplayItemReferences from './display_item_references'
import { ImageStatusStrings } from 'models/status'
import type { Action } from 'models/table_item'

interface ItemLinkageProps {
  item: Item
  action: Action
  handleItemOpen: (itemUid: string) => void
}

export default function ItemLinkage({
  item,
  action,
  handleItemOpen,
}: ItemLinkageProps): ReactElement {
  if (isSampleItem(item)) {
    return (
      <React.Fragment>
        <DisplayItemReferences
          title="Parents"
          action={action}
          references={item.parents}
          handleItemOpen={handleItemOpen}
        />
        <DisplayItemReferences
          title="Children"
          action={action}
          references={item.children}
          handleItemOpen={handleItemOpen}
        />
      </React.Fragment>
    )
  }
  if (isImageItem(item)) {
    return (
      <React.Fragment>
        <TextField label="Status" value={ImageStatusStrings[item.status]} />
        <DisplayItemReferences
          title="Samples"
          action={action}
          references={item.samples}
          handleItemOpen={handleItemOpen}
        />
      </React.Fragment>
    )
  }
  if (isObservationItem(item)) {
    return (
      <DisplayItemReferences
        title="Observed on"
        action={action}
        references={[item.item]}
        handleItemOpen={handleItemOpen}
      />
    )
  }
  return <></>
}
