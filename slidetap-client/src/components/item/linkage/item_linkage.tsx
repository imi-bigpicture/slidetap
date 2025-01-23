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
import type { Item } from 'src/models/item'

import type { Action } from 'src/models/action'
import { isImageItem, isObservationItem, isSampleItem } from 'src/models/helpers'

import ImageLinkage from './image_linkage'
import ObservationLinkage from './observation_linkage'
import SampleLinkage from './sample_linkage'

interface ItemLinkageProps {
  item: Item
  action: Action
  handleItemOpen: (itemUid: string) => void
  setItem: (value: Item) => void
}

export default function ItemLinkage({
  item,
  action,
  handleItemOpen,
  setItem,
}: ItemLinkageProps): ReactElement {
  if (isSampleItem(item)) {
    return (
      <SampleLinkage
        item={item}
        action={action}
        handleItemOpen={handleItemOpen}
        setItem={setItem}
      />
    )
  }
  if (isImageItem(item)) {
    return (
      <ImageLinkage
        item={item}
        action={action}
        handleItemOpen={handleItemOpen}
        setItem={setItem}
      />
    )
  }
  if (isObservationItem(item)) {
    return (
      <ObservationLinkage
        item={item}
        action={action}
        handleItemOpen={handleItemOpen}
        setItem={setItem}
      />
    )
  }
  return <></>
}
