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
import { useParams } from 'react-router-dom'
import DisplayItemDetails from 'src/components/item/item_details'

import { ItemDetailAction } from 'src/models/action'
export default function ItemPage(): ReactElement {
  const { projectUid, itemUid, action } = useParams()
  if (projectUid === undefined) {
    throw new Error('Project UID is required to display item page')
  }
  if (itemUid === undefined) {
    throw new Error('Item UID is required to display item page')
  }
  const [itemDetailsOpen, setItemDetailsOpen] = React.useState(true)
  const [itemDetailUid, setItemDetailUid] = React.useState<string>(itemUid)
  const [itemDetailAction, setItemDetailAction] = React.useState<ItemDetailAction>(
    action !== undefined
      ? (action as unknown as ItemDetailAction)
      : ItemDetailAction.VIEW,
  )
  const [privateOpen, setPrivateOpen] = React.useState(false)
  const [previewOpen, setPreviewOpen] = React.useState(false)

  React.useEffect(() => {
    if (!itemDetailsOpen) {
      window.close()
    }
  }, [itemDetailsOpen])

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
      windowed={true}
    />
  )
}
