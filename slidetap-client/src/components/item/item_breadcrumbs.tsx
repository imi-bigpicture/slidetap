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

import HomeIcon from '@mui/icons-material/Home'
import { Breadcrumbs, Link } from '@mui/material'

interface ItemBreadcrumbsProps {
  openedItems: { identifier: string; uid: string }[]
  handleChangeItem: (identifier: string, uid: string) => void
  setOpenedItems: (items: { identifier: string; uid: string }[]) => void
  setItemUid: (uid: string) => void
}

export default function ItemBreadcrumbs({
  openedItems,
  handleChangeItem,
  setOpenedItems,
  setItemUid,
}: ItemBreadcrumbsProps): JSX.Element {
  return (
    <Breadcrumbs aria-label="breadcrumb">
      <Link
        onClick={() => {
          const firstItem = openedItems[0]
          setOpenedItems(openedItems.slice(0, 1))
          setItemUid(firstItem.uid)
        }}
      >
        <HomeIcon />
      </Link>
      {openedItems.slice(1).map((item) => {
        return (
          <Link
            key={item.uid}
            onClick={() => {
              handleChangeItem(item.identifier, item.uid)
            }}
          >
            {item.identifier}
          </Link>
        )
      })}
    </Breadcrumbs>
  )
}
