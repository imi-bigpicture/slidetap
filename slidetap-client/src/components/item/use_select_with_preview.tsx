//    Copyright 2026 SECTRA AB
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
import type { SelectionTree } from 'src/models/item_select'
import itemApi from 'src/services/api/item_api'
import SelectionTreeDialog from './selection_tree_dialog'

interface PendingSelection {
  itemUid: string
  select: boolean
  subject: string
  /** Already worked out to decide whether to ask, so not asked for again. */
  trees: SelectionTree[]
}

interface SelectWithPreview {
  /** Select or deselect an item. Applied at once when nothing else would
   * change with it; otherwise the tree of what could is shown to choose from
   * first. */
  request: (itemUid: string, select: boolean, subject?: string) => Promise<void>
  /** The dialog, to render wherever the caller renders. */
  dialog: ReactElement | null
  isPending: boolean
}

/** Selection from a one-click button, choosing what goes with it when
 * anything does. */
export function useSelectWithPreview({
  onApplied,
  onError,
}: {
  onApplied: () => void
  onError: (error: unknown) => void
}): SelectWithPreview {
  const [pending, setPending] = useState<PendingSelection | null>(null)
  const [isPending, setIsPending] = useState(false)

  const request = async (
    itemUid: string,
    select: boolean,
    subject = 'this item',
  ): Promise<void> => {
    setIsPending(true)
    try {
      const trees = await itemApi.selectionTrees([itemUid], select)
      if (trees.some((tree) => tree.up.length > 0 || tree.down.length > 0)) {
        setPending({ itemUid, select, subject, trees })
        return
      }
      await itemApi.selectMany({
        itemUids: [itemUid],
        select,
        items: [],
        comment: null,
        tags: null,
        additiveTags: false,
      })
      onApplied()
    } catch (error) {
      onError(error)
    } finally {
      setIsPending(false)
    }
  }

  const dialog =
    pending === null ? null : (
      <SelectionTreeDialog
        itemUids={[pending.itemUid]}
        initialTrees={pending.trees}
        select={pending.select}
        subject={pending.subject}
        onClose={() => setPending(null)}
        onApplied={onApplied}
        onError={onError}
      />
    )

  return { request, dialog, isPending }
}
