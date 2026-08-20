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

import { useState, type ReactElement } from 'react'
import DisplayItemDetails from 'src/components/item/item_details'
import { ItemDetailAction } from 'src/models/action'

interface DetailDock {
  /** The panel to hand to a `SplitPanel`, or false while nothing is open. */
  panel: ReactElement | false
  /** Open an item beside the view. The siblings are what stepping through the
   * panel walks, in reading order; pass the whole view's items. */
  open: (itemUid: string, siblingUids: string[]) => void
  /** What is open, so a view can mark it apart from the rest. */
  openedUid: string
}

/**
 * An item detail panel docked beside whatever is being worked from.
 *
 * Docked rather than navigated to: the view is the place being worked from,
 * and losing it to look at one item costs the reader their place.
 */
export function useDetailDock(projectUid: string): DetailDock {
  // Empty rather than null for the closed state, matching the curate panel it
  // shares its props with.
  const [itemUid, setItemUid] = useState('')
  const [siblings, setSiblings] = useState<string[]>([])
  const [action, setAction] = useState<ItemDetailAction>(ItemDetailAction.EDIT)
  const [privateOpen, setPrivateOpen] = useState(false)
  const [previewOpen, setPreviewOpen] = useState(false)

  return {
    openedUid: itemUid,
    open: (uid, siblingUids) => {
      setSiblings(siblingUids)
      setItemUid(uid)
    },
    panel: itemUid !== '' && (
      <DisplayItemDetails
        projectUid={projectUid}
        itemUid={itemUid}
        action={action}
        privateOpen={privateOpen}
        previewOpen={previewOpen}
        setOpen={(open) => {
          if (!open) setItemUid('')
        }}
        setItemUid={setItemUid}
        setItemAction={setAction}
        setPrivateOpen={setPrivateOpen}
        setPreviewOpen={setPreviewOpen}
        windowed={false}
        itemUids={siblings}
      />
    ),
  }
}
