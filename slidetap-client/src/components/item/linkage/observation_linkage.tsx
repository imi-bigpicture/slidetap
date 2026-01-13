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

import { ReactElement } from 'react'
import { ItemDetailAction } from 'src/models/action'
import { Observation } from 'src/models/item'
import DisplayObservationAnnotation from '../reference/display_observation_annotation'
import DisplayObservationImage from '../reference/display_observation_image'
import DisplayObservationSample from '../reference/display_observation_sample'

interface ObservationLinkageProps {
  item: Observation
  action: ItemDetailAction
  handleItemOpen: (name: string, uid: string) => void

  setItem: (value: Observation) => void
}

export default function ObservationLinkage({
  item,
  action,
  handleItemOpen,
  setItem,
}: ObservationLinkageProps): ReactElement {
  const handleObservationItemsUpdate = (
    schema_uid: string,
    references: string[],
  ): void => {
    const updatedItemItem: [string, string] = [schema_uid, references[0]]
    const updatedItem = { ...item, item: updatedItemItem }
    setItem(updatedItem)
  }

  const relation = [item.image, item.sample, item.annotation].find(
    (relation) => relation !== null,
  )
  if (relation === undefined) {
    return <></>
  }
  if (relation == item.sample) {
    return (
      <DisplayObservationSample
        action={action}
        schemaUid={item.schemaUid}
        references={{ [item.sample[0]]: [item.sample[1]] }}
        datasetUid={item.datasetUid}
        batchUid={item.batchUid}
        handleItemOpen={handleItemOpen}
        handleItemReferencesUpdate={handleObservationItemsUpdate}
      />
    )
  }
  if (relation == item.image) {
    return (
      <DisplayObservationImage
        action={action}
        schemaUid={item.schemaUid}
        references={{ [item.image[0]]: [item.image[1]] }}
        datasetUid={item.datasetUid}
        batchUid={item.batchUid}
        handleItemOpen={handleItemOpen}
        handleItemReferencesUpdate={handleObservationItemsUpdate}
      />
    )
  }
  if (relation == item.annotation) {
    return (
      <DisplayObservationAnnotation
        action={action}
        schemaUid={item.schemaUid}
        references={{ [item.annotation[0]]: [item.annotation[1]] }}
        datasetUid={item.datasetUid}
        batchUid={item.batchUid}
        handleItemOpen={handleItemOpen}
        handleItemReferencesUpdate={handleObservationItemsUpdate}
      />
    )
  }
  throw new Error('Invalid observation relation')
}
