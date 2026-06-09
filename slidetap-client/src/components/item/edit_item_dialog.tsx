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

import { Dialog, DialogContent } from '@mui/material'
import { useEffect, useState, type ReactElement } from 'react'
import DisplayItemDetails from 'src/components/item/item_details'
import { ItemDetailAction } from 'src/models/action'

interface EditItemDialogProps {
  projectUid: string
  /** UID of the item to edit. When null, the dialog is closed. */
  itemUid: string | null
  onClose: () => void
}

export default function EditItemDialog({
  projectUid,
  itemUid,
  onClose,
}: EditItemDialogProps): ReactElement | null {
  const [internalItemUid, setInternalItemUid] = useState<string>(itemUid ?? '')
  const [action, setAction] = useState<ItemDetailAction>(ItemDetailAction.EDIT)
  const [privateOpen, setPrivateOpen] = useState(false)
  const [previewOpen, setPreviewOpen] = useState(false)

  useEffect(() => {
    if (itemUid) {
      setInternalItemUid(itemUid)
      setAction(ItemDetailAction.EDIT)
    }
  }, [itemUid])

  if (!itemUid) return null

  const handleSetOpen: React.Dispatch<React.SetStateAction<boolean>> = (value) => {
    const next = typeof value === 'function' ? value(true) : value
    if (!next) onClose()
  }

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="lg">
      <DialogContent sx={{ p: 1 }}>
        <DisplayItemDetails
          projectUid={projectUid}
          itemUid={internalItemUid}
          action={action}
          privateOpen={privateOpen}
          previewOpen={previewOpen}
          setOpen={handleSetOpen}
          setItemUid={setInternalItemUid}
          setItemAction={setAction}
          setPrivateOpen={setPrivateOpen}
          setPreviewOpen={setPreviewOpen}
          windowed={false}
        />
      </DialogContent>
    </Dialog>
  )
}
