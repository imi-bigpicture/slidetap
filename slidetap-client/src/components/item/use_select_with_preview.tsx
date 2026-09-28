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

import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
} from '@mui/material'
import { useState, type ReactElement } from 'react'
import type { ItemSelect, ItemSelectResult } from 'src/models/item_select'
import itemApi from 'src/services/api/item_api'
import SelectionPreview, { needsConfirmation } from './selection_preview'

interface PendingSelection {
  itemUid: string
  subject: string
  value: ItemSelect
  preview: ItemSelectResult
}

interface SelectWithPreview {
  /** Select or deselect an item. Applied at once when all it does is reach
   * down; shown for confirmation first when it reaches up, leaves something
   * not valid, or meets what a curator took out by hand. */
  request: (itemUid: string, select: boolean, subject?: string) => Promise<void>
  /** The confirmation dialog, to render wherever the caller renders. */
  dialog: ReactElement | null
  isPending: boolean
}

/** Selection from a one-click button, with a preview when it matters. */
export function useSelectWithPreview({
  onApplied,
  onError,
}: {
  onApplied: () => void
  onError: (error: unknown) => void
}): SelectWithPreview {
  const [pending, setPending] = useState<PendingSelection | null>(null)
  const [isPending, setIsPending] = useState(false)

  const apply = async (itemUid: string, value: ItemSelect): Promise<void> => {
    setIsPending(true)
    try {
      await itemApi.select(itemUid, { ...value, dryRun: false })
      onApplied()
    } catch (error) {
      onError(error)
    } finally {
      setIsPending(false)
    }
  }

  const request = async (
    itemUid: string,
    select: boolean,
    subject = 'this item',
  ): Promise<void> => {
    const value: ItemSelect = { select, comment: null, tags: null, additiveTags: false }
    setIsPending(true)
    let preview: ItemSelectResult
    try {
      preview = await itemApi.select(itemUid, { ...value, dryRun: true })
    } catch (error) {
      setIsPending(false)
      onError(error)
      return
    }
    setIsPending(false)
    if (needsConfirmation(preview)) {
      setPending({ itemUid, subject, value, preview })
      return
    }
    await apply(itemUid, value)
  }

  const confirm = (overrideCuration: boolean): void => {
    if (pending === null) {
      return
    }
    const { itemUid, value } = pending
    setPending(null)
    void apply(itemUid, { ...value, overrideCuration })
  }

  const dialog =
    pending === null ? null : (
      <Dialog open onClose={() => setPending(null)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {pending.value.select
            ? `Restore ${pending.subject} to the project?`
            : `Remove ${pending.subject} from the project?`}
        </DialogTitle>
        <DialogContent>
          <SelectionPreview
            result={pending.preview}
            loading={false}
            select={pending.value.select}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPending(null)}>Cancel</Button>
          {pending.value.select && pending.preview.keptOut.length > 0 && (
            <Button onClick={() => confirm(true)}>Also bring those back</Button>
          )}
          <Button variant="contained" onClick={() => confirm(false)}>
            {pending.value.select ? 'Restore' : 'Remove'}
          </Button>
        </DialogActions>
      </Dialog>
    )

  return { request, dialog, isPending }
}
