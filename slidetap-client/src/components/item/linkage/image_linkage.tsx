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

import { Stack, TextField } from '@mui/material'
import { ReactElement } from 'react'
import { ItemDetailAction } from 'src/models/action'
import { ImageStatusStrings } from 'src/models/image_status'
import { Image } from 'src/models/item'
import DisplayImageAnnotations from '../reference/display_image_annotations'
import DisplayImageObservations from '../reference/display_image_observations'
import DisplayImageRelations from '../reference/display_image_samples'

interface ImageLinkageProps {
  item: Image
  action: ItemDetailAction
  handleItemOpen: (name: string, uid: string) => void
  setItem: (value: Image) => void
}

export default function ImageLinkage({
  item,
  action,
  handleItemOpen,
  setItem,
}: ImageLinkageProps): ReactElement {
  const handleImageSamplesUpdate = (schema_uid: string, references: string[]): void => {
    const updatedItem = {
      ...item,
      samples: { ...item.samples, [schema_uid]: references },
    }
    setItem(updatedItem)
  }
  const handleImageAnnotationsUpdate = (
    schema_uid: string,
    references: string[],
  ): void => {
    const updatedItem = {
      ...item,
      observations: { ...item.observations, [schema_uid]: references },
    }
    setItem(updatedItem)
  }
  const handleImageObservationsUpdate = (
    schema_uid: string,
    references: string[],
  ): void => {
    const updatedItem = {
      ...item,
      observations: { ...item.observations, [schema_uid]: references },
    }
    setItem(updatedItem)
  }

  return (
    <Stack direction="column" spacing={1}>
      <TextField
        slotProps={{
          input: {
            readOnly: true,
          },
          inputLabel: {
            shrink: true,
          },
        }}
        label="Status"
        value={ImageStatusStrings[item.status]}
      />
      <DisplayImageRelations
        action={action}
        schemaUid={item.schemaUid}
        references={item.samples}
        datasetUid={item.datasetUid}
        batchUid={item.batchUid}
        handleItemOpen={handleItemOpen}
        handleItemReferencesUpdate={handleImageSamplesUpdate}
      />
      <DisplayImageAnnotations
        action={action}
        schemaUid={item.schemaUid}
        references={item.samples}
        datasetUid={item.datasetUid}
        batchUid={item.batchUid}
        handleItemOpen={handleItemOpen}
        handleItemReferencesUpdate={handleImageAnnotationsUpdate}
      />
      <DisplayImageObservations
        action={action}
        schemaUid={item.schemaUid}
        references={item.samples}
        datasetUid={item.datasetUid}
        batchUid={item.batchUid}
        handleItemOpen={handleItemOpen}
        handleItemReferencesUpdate={handleImageObservationsUpdate}
      />
    </Stack>
  )
}
