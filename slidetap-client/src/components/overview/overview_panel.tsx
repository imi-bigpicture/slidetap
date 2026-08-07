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
import OverviewView, {
  type OverviewEditState,
} from 'src/components/overview/overview_view'
import SplitPanel from 'src/components/split_panel'
import { ItemDetailAction } from 'src/models/action'
import type { OverviewLayout } from 'src/models/schema/overview_layout'
import type { TableRequest } from 'src/models/table_item'

interface OverviewPanelProps {
  projectUid: string
  itemUid: string
  overviewLayout: OverviewLayout
  batchUid?: string
  tableRequest?: TableRequest
  /** Leave the overview's own identifier and navigation bar out, for a caller
   * that draws one of its own. */
  hideHeader?: boolean
  /** Reports what save and revert buttons drawn outside the overview need. */
  onEditStateChange?: (state: OverviewEditState) => void
}

/**
 * An overview with the item detail panel docked beside it.
 *
 * Opening an item from a chip docks it rather than navigating to it: the
 * overview is the place being worked from, and losing it to look at one item
 * costs the reader their place in the case.
 *
 * Fills whatever height it is given — the caller decides that, since the
 * overview page owns the window while the review view shares it.
 */
export default function OverviewPanel({
  projectUid,
  itemUid,
  overviewLayout,
  batchUid,
  tableRequest,
  hideHeader,
  onEditStateChange,
}: OverviewPanelProps): ReactElement {
  // Empty rather than null for the closed state, matching the curate panel it
  // shares its props with.
  const [detailUid, setDetailUid] = useState('')
  const [detailSiblings, setDetailSiblings] = useState<string[]>([])
  const [detailAction, setDetailAction] = useState<ItemDetailAction>(
    ItemDetailAction.EDIT,
  )
  const [privateOpen, setPrivateOpen] = useState(false)
  const [previewOpen, setPreviewOpen] = useState(false)

  return (
    <SplitPanel
      fillHeight
      panel={
        detailUid !== '' && (
          <DisplayItemDetails
            projectUid={projectUid}
            itemUid={detailUid}
            action={detailAction}
            privateOpen={privateOpen}
            previewOpen={previewOpen}
            setOpen={(open) => {
              if (!open) setDetailUid('')
            }}
            setItemUid={setDetailUid}
            setItemAction={setDetailAction}
            setPrivateOpen={setPrivateOpen}
            setPreviewOpen={setPreviewOpen}
            windowed={false}
            itemUids={detailSiblings}
          />
        )
      }
    >
      <OverviewView
        projectUid={projectUid}
        itemUid={itemUid}
        overviewLayout={overviewLayout}
        batchUid={batchUid}
        tableRequest={tableRequest}
        hideHeader={hideHeader}
        onEditStateChange={onEditStateChange}
        openedItemUid={detailUid}
        onOpenItem={(uid, siblings) => {
          setDetailSiblings(siblings)
          setDetailUid(uid)
        }}
      />
    </SplitPanel>
  )
}
