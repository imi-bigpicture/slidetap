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

import { type ReactElement } from 'react'
import { useDetailDock } from 'src/components/item/detail_dock'
import OverviewView, {
  type OverviewEditState,
} from 'src/components/overview/overview_view'
import SplitPanel from 'src/components/split_panel'
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
  /** Step to another item by telling the caller — see `OverviewView`. */
  onNavigateToItem?: (itemUid: string) => void
}

/**
 * An overview with the item detail panel docked beside it.
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
  onNavigateToItem,
}: OverviewPanelProps): ReactElement {
  const dock = useDetailDock(projectUid)

  return (
    <SplitPanel fillHeight panel={dock.panel}>
      <OverviewView
        projectUid={projectUid}
        itemUid={itemUid}
        overviewLayout={overviewLayout}
        batchUid={batchUid}
        tableRequest={tableRequest}
        hideHeader={hideHeader}
        onEditStateChange={onEditStateChange}
        onNavigateToItem={onNavigateToItem}
        openedItemUid={dock.openedUid}
        onOpenItem={dock.open}
      />
    </SplitPanel>
  )
}
