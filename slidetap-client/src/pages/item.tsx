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

import React, { ReactElement } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import DisplayItemDetails from 'src/components/item/item_details'
import useItemStepping from 'src/components/item/use_item_stepping'

import { ItemDetailAction } from 'src/models/action'
export default function ItemPage(): ReactElement {
  const { projectUid, itemUid, action } = useParams()
  const navigate = useNavigate()
  if (projectUid === undefined) {
    throw new Error('Project UID is required to display item page')
  }
  if (itemUid === undefined) {
    throw new Error('Item UID is required to display item page')
  }
  const [itemDetailsOpen, setItemDetailsOpen] = React.useState(true)
  const [itemDetailUid, setItemDetailUid] = React.useState<string>(itemUid)
  // Editable unless the route asks otherwise, the same as the curation panel
  // this page opens items from.
  const [itemDetailAction, setItemDetailAction] = React.useState<ItemDetailAction>(
    action !== undefined
      ? (action as unknown as ItemDetailAction)
      : ItemDetailAction.EDIT,
  )
  const stepping = useItemStepping(
    itemDetailUid,
    (uid) => `/project/${projectUid}/item/${uid}`,
  )
  // Followed rather than held: stepping changes the address, and the item shown
  // is whichever one the address names.
  React.useEffect(() => {
    if (itemUid !== undefined) {
      setItemDetailUid(itemUid)
    }
  }, [itemUid])
  const [privateOpen, setPrivateOpen] = React.useState(false)
  const [previewOpen, setPreviewOpen] = React.useState(false)

  // Closing goes back to whatever the item was opened from: this is a page in
  // the application now rather than a window of its own to be shut.
  React.useEffect(() => {
    if (!itemDetailsOpen) {
      navigate(-1)
    }
  }, [itemDetailsOpen, navigate])

  return (
    <DisplayItemDetails
      projectUid={projectUid}
      itemUid={itemDetailUid}
      action={itemDetailAction}
      privateOpen={privateOpen}
      previewOpen={previewOpen}
      setOpen={setItemDetailsOpen}
      setItemUid={setItemDetailUid}
      setItemAction={setItemDetailAction}
      setPrivateOpen={setPrivateOpen}
      setPreviewOpen={setPreviewOpen}
      windowed={false}
      pageHeader
      stepping={stepping}
    />
  )
}
