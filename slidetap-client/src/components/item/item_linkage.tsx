import type { Item } from 'models/items'
import React, { type ReactElement } from 'react'
import { TextField } from '@mui/material'

import { isImageItem, isObservationItem, isSampleItem } from 'models/helpers'
import DisplayItemReferences from './display_item_references'

interface ItemLinkageProps {
  item: Item
  handleItemOpen: (itemUid: string) => void
}

export default function ItemLinkage({
  item,
  handleItemOpen,
}: ItemLinkageProps): ReactElement {
  if (isSampleItem(item)) {
    return (
      <React.Fragment>
        <DisplayItemReferences
          title="Parents"
          references={item.parents}
          handleItemOpen={handleItemOpen}
        />
        <DisplayItemReferences
          title="Children"
          references={item.children}
          handleItemOpen={handleItemOpen}
        />
      </React.Fragment>
    )
  }
  if (isImageItem(item)) {
    return (
      <React.Fragment>
        <TextField label="Status" value={item.status} />
        <DisplayItemReferences
          title="Samples"
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
        references={[item.observedOn]}
        handleItemOpen={handleItemOpen}
      />
    )
  }
  return <></>
}
